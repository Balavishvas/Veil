const video=document.getElementById("source"),canvas=document.getElementById("output"),ctx=canvas.getContext("2d");
const start=document.getElementById("start"),stop=document.getElementById("stop"),record=document.getElementById("record"),present=document.getElementById("present");
const preflight=document.getElementById("preflight"),preflightState=document.getElementById("preflightState"),preflightDetail=document.getElementById("preflightDetail"),continueBtn=document.getElementById("continueBtn");
let stream=null,ws=null,running=false,busy=false,boxes=[],mode="blur",recorder=null,chunks=[],seconds=0,timer=null,fw=1,fh=1,lastFindingsAt=0,preflightRunning=false,preflightSamples=0,preflightHits=0;

document.querySelectorAll(".modes button").forEach(b=>b.onclick=()=>{document.querySelectorAll(".modes button").forEach(x=>x.classList.remove("active"));b.classList.add("active");mode=b.dataset.mode});

function risk(v,s){document.getElementById("risk").textContent=v==null?"—":String(v).padStart(2,"0");document.getElementById("bar").style.width=(v||0)+"%";document.getElementById("riskText").textContent=s||"WAITING"}
function list(items){document.getElementById("count").textContent=String(items.length).padStart(2,"0");document.getElementById("findings").innerHTML=items.length?items.map((x,i)=>`<div class="finding"><b>0${i+1}</b><div><b>${x.label}</b><span> ${x.w} × ${x.h}px</span></div></div>`).join(""):'<p class="empty">No regions identified.</p>'}

function draw(){
  if(!running||video.readyState<2)return;
  canvas.width=video.videoWidth; canvas.height=video.videoHeight;
  ctx.drawImage(video,0,0);
  const now=performance.now();
  // Keep a detected region masked for a short safety window after OCR misses it.
  const activeBoxes=(now-lastFindingsAt<1800)?boxes:[];
  activeBoxes.forEach(b=>{
    let x=b.x*canvas.width/fw,y=b.y*canvas.height/fh,w=b.w*canvas.width/fw,h=b.h*canvas.height/fh;
    x=Math.max(0,x-4);y=Math.max(0,y-4);w=Math.min(canvas.width-x,w+8);h=Math.min(canvas.height-y,h+8);
    if(mode==="redact"){
      ctx.fillStyle="#11110f";ctx.fillRect(x,y,w,h);ctx.fillStyle="#c9ff45";ctx.font="10px IBM Plex Mono";ctx.fillText("VEIL / REDACTED",x+6,y+h/2+3);
    }else if(mode==="pixel"){
      let t=document.createElement("canvas"),tw=Math.max(1,Math.ceil(w/16)),th=Math.max(1,Math.ceil(h/16)),tc=t.getContext("2d");
      t.width=tw;t.height=th;tc.imageSmoothingEnabled=false;tc.drawImage(canvas,x,y,w,h,0,0,tw,th);ctx.imageSmoothingEnabled=false;ctx.drawImage(t,0,0,tw,th,x,y,w,h);ctx.imageSmoothingEnabled=true;
    }else{
      ctx.save();ctx.filter="blur(18px)";ctx.drawImage(canvas,x-18,y-18,w+36,h+36,x-18,y-18,w+36,h+36);ctx.restore();
    }
  });
}

function send(){
  if(!running||busy||!ws||ws.readyState!==1||video.readyState<2)return;
  busy=true;
  let t=document.createElement("canvas"),scale=Math.min(1,1280/video.videoWidth);
  t.width=Math.round(video.videoWidth*scale);t.height=Math.round(video.videoHeight*scale);
  t.getContext("2d").drawImage(video,0,0,t.width,t.height);
  t.toBlob(blob=>{
    let r=new FileReader;r.onload=()=>{ws.send(r.result.split(",")[1]);fw=t.width;fh=t.height};r.readAsDataURL(blob)
  },"image/jpeg",.72);
}

function socket(){
  let p=location.protocol==="https:"?"wss":"ws";
  ws=new WebSocket(p+"://"+location.host+"/ws/protect");
  ws.onmessage=e=>{
    busy=false;
    let d=JSON.parse(e.data);
    if(d.error){preflightDetail.textContent="OCR error: "+d.error;return}
    boxes=d.findings||[];
    if(boxes.length)lastFindingsAt=performance.now();
    risk(d.risk,d.status);list(boxes);
    document.getElementById("frame").textContent=d.frame_width+" × "+d.frame_height;
    document.getElementById("maskState").textContent=boxes.length?boxes.length+" REGION"+(boxes.length>1?"S":"")+" MASKED":"MASKING READY";

    if(preflightRunning){
      preflightSamples++;
      if(boxes.length)preflightHits++;
      if(preflightSamples>=3){
        preflightRunning=false;
        preflight.classList.add("show");
        if(preflightHits){
          preflightState.textContent="EXPOSURE DETECTED";
          preflightState.className="danger";
          preflightDetail.textContent=preflightHits+" of 3 scan samples contained sensitive regions. They are being masked on the protected output.";
        }else{
          preflightState.textContent="SCAN CLEAR";
          preflightState.className="safe";
          preflightDetail.textContent="No known sensitive patterns were detected in the initial scan. Continue only if you are sharing the Veil protected window.";
        }
        continueBtn.disabled=false;
      }
    }
  };
  ws.onerror=()=>{preflightDetail.textContent="Protection engine connection failed. Restart Veil and try again."}
}

async function begin(){
  try{
    stream=await navigator.mediaDevices.getDisplayMedia({video:{frameRate:30},audio:false});
    video.srcObject=stream;await video.play();running=true;
    document.getElementById("idle").style.display="none";document.querySelector(".workspace").classList.add("active");
    document.getElementById("state").textContent="SCANNING";start.disabled=true;stop.disabled=false;record.disabled=true;present.disabled=true;
    preflightRunning=true;preflightSamples=0;preflightHits=0;preflightState.textContent="SCANNING SOURCE";preflightState.className="scanning";preflightDetail.textContent="Veil is checking the selected source before protected mode starts.";continueBtn.disabled=true;preflight.classList.add("show");
    socket();
    stream.getVideoTracks()[0].onended=end;
  }catch(e){console.error(e)}
}

function continueSession(){
  preflight.classList.remove("show");
  document.getElementById("state").textContent="PROTECTED";
  record.disabled=false;present.disabled=false;
  document.getElementById("shareHint").classList.add("show");
}

function rec(){
  if(recorder?.state==="recording"){recorder.stop();record.textContent="● RECORD";return}
  chunks=[];recorder=new MediaRecorder(canvas.captureStream(30),{mimeType:"video/webm"});
  recorder.ondataavailable=e=>e.data.size&&chunks.push(e.data);
  recorder.onstop=()=>{let a=document.createElement("a");a.href=URL.createObjectURL(new Blob(chunks,{type:"video/webm"}));a.download="veil-session.webm";a.click()};
  recorder.start();record.textContent="■ STOP RECORDING";
}

function view(){
  let w=window.open("","veil","width=1280,height=720");
  if(!w)return;
  w.document.write('<title>Veil — Protected Output</title><style>html,body{margin:0;background:#090908;height:100%;display:grid;place-items:center;color:#aaa;font:14px monospace}canvas{max-width:100%;max-height:100%}</style><canvas id="c"></canvas>');
  let c=w.document.getElementById("c"),x=c.getContext("2d");
  (function loop(){if(w.closed||!running)return;c.width=canvas.width;c.height=canvas.height;x.drawImage(canvas,0,0);requestAnimationFrame(loop)})();
}

function end(){
  running=false;clearInterval(timer);if(recorder?.state==="recording")recorder.stop();ws?.close();stream?.getTracks().forEach(t=>t.stop());video.srcObject=null;stream=null;boxes=[];busy=false;lastFindingsAt=0;
  start.disabled=false;stop.disabled=true;record.disabled=true;present.disabled=true;record.textContent="● RECORD";
  document.querySelector(".workspace").classList.remove("active");document.getElementById("idle").style.display="flex";document.getElementById("state").textContent="STANDBY";document.getElementById("frame").textContent="NO SIGNAL";document.getElementById("maskState").textContent="MASKING OFF";document.getElementById("clock").textContent="00:00";
  document.getElementById("shareHint").classList.remove("show");preflight.classList.remove("show");risk(null,"WAITING");list([])
}

start.onclick=begin;continueBtn.onclick=continueSession;stop.onclick=end;record.onclick=rec;present.onclick=view;
setInterval(()=>{if(running){draw();send()}},400);
setInterval(()=>{if(running&&document.getElementById("state").textContent==="PROTECTED"){seconds++;document.getElementById("clock").textContent=String(Math.floor(seconds/60)).padStart(2,"0")+":"+String(seconds%60).padStart(2,"0")}},1000);
