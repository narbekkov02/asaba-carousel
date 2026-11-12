"""Render a daily silent video: <part.html> (must define window.render(t), window.T_END, window.SFX)
+ the 3D book CTA (kit/cta/cta.html, 14.5 s), ambient bed + SFX, loudness -18 LUFS.
Usage: python3 make_video.py path/to/part.html out.mp4
Needs: fonts from kit/fonts copied to ~/.fonts (fc-cache -f), Chrome at /usr/bin/google-chrome, ffmpeg."""
import sys, pathlib, wave, subprocess, numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
part=pathlib.Path(sys.argv[1]).resolve(); out=pathlib.Path(sys.argv[2]).resolve()
KIT=pathlib.Path(__file__).resolve().parent.parent
work=out.parent/('work_'+out.stem); fr=work/'frames'; fr.mkdir(parents=True,exist_ok=True)
for f in fr.glob('*.jpg'): f.unlink()
fps=30; TB=14.5
with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  pg=b.new_page(viewport={'width':1080,'height':1920}); pg.goto(part.as_uri()); pg.wait_for_timeout(800)
  T1=float(pg.evaluate('window.T_END')); SFX=pg.evaluate('window.SFX||[]')
  pb=b.new_page(viewport={'width':1080,'height':1920}); pb.goto((KIT/'cta'/'cta.html').as_uri()); pb.wait_for_timeout(800)
  T=T1+TB; n=int(round(T*fps))
  for i in range(n):
    t=i/fps; o=str(fr/f'f{i:05d}.jpg')
    if t<T1: pg.evaluate(f'render({t})'); pg.screenshot(path=o,type='jpeg',quality=92)
    else:
      pb.evaluate(f'render({t-T1})'); pb.screenshot(path=o,type='jpeg',quality=92)
      k=(t-T1)/0.2
      if k<1: im=Image.open(o); Image.blend(im,Image.new('RGB',im.size,'white'),0.5*(1-k)).save(o,quality=92)
  b.close()
sr=48000; N=int(T*sr); tt=np.arange(N)/sr; rng=np.random.default_rng(7)
w=rng.standard_normal(N); br=np.cumsum(w); br-=np.convolve(br,np.ones(4800)/4800,mode='same'); br/=np.max(np.abs(br))
pad=np.zeros(N); chords=[[110,164.81,261.63],[87.31,130.81,220.0],[98.0,146.83,246.94],[82.41,123.47,207.65]]; cl=8.0
for ci in range(int(T/cl)+1):
  ch=chords[ci%4]; a=int(ci*cl*sr); bnd=min(N,int((ci+1)*cl*sr+2*sr))
  if a>=N: break
  sg=np.arange(bnd-a)/sr; e=np.clip(np.minimum(sg/2.5,((bnd-a)/sr-sg)/2.5),0,1)
  pad[a:bnd]+=sum(np.sin(2*np.pi*f*sg)*(0.5+0.5*np.sin(2*np.pi*0.13*sg+j))+0.3*np.sin(2*np.pi*f*2.003*sg) for j,f in enumerate(ch))*e
pad/=np.max(np.abs(pad)); bed=(0.5*br+0.5*pad)*np.minimum(1,np.minimum(tt/2.0,(T-tt)/2.5))
def env(m,a,d):
  e=np.ones(m); ai=max(1,int(a*sr)); e[:ai]=np.linspace(0,1,ai); e*=np.exp(-np.arange(m)/(d*sr)); return e
def whoosh(dur=0.45,g=1.6):
  m=int(dur*sr); nz=rng.standard_normal(m); y=np.zeros(m); a=np.linspace(0.02,0.25,m); v=0
  for i in range(m): v+=a[i]*(nz[i]-v); y[i]=v
  return y*np.sin(np.linspace(0,np.pi,m))**2*g
def thud(g=1.0,d=0.11): m=int(0.5*sr); f=np.linspace(120,42,m); return np.sin(2*np.pi*np.cumsum(f)/sr)*env(m,0.002,d)*g
def pop(g=0.8): m=int(0.12*sr); f=np.linspace(900,500,m); return np.sin(2*np.pi*np.cumsum(f)/sr)*env(m,0.003,0.03)*g
def tick(g=0.4): m=int(0.04*sr); x=np.arange(m)/sr; return np.sin(2*np.pi*2400*x)*env(m,0.001,0.006)*g
def ding(g=0.45,f0=1320): m=int(1.0*sr); x=np.arange(m)/sr; return (np.sin(2*np.pi*f0*x)+0.5*np.sin(2*np.pi*2*f0*x)+0.25*np.sin(2*np.pi*1.5*f0*x))*env(m,0.002,0.28)*g
def flip(): m=int(0.06*sr); nz=rng.standard_normal(m); y=np.diff(np.concatenate([[0],nz])); return y*env(m,0.002,0.012)*0.55
LIB={'whoosh':lambda:whoosh(),'whooshS':lambda:whoosh(0.3,0.8),'thud':lambda:thud(0.9),'thudBig':lambda:thud(1.4,0.18),'pop':lambda:pop(),'popS':lambda:pop(0.5),'tick':lambda:tick(),'ding':lambda:ding()}
sfx=np.zeros(N+sr)
def add(t,s): i=int(t*sr); sfx[i:i+len(s)]+=s[:max(0,len(sfx)-i)]
for t,k in SFX: add(float(t),LIB.get(k,LIB['pop'])())
o=T1
add(o,whoosh(0.9)); add(o+1.15,thud(0.7)); add(o+1.4,whoosh(0.8,1.2)); add(o+3.0,whoosh(0.4,0.9)); add(o+3.75,thud(1.0))
for i in range(16): add(o+4.4+i*0.095+0.12,flip())
for k in range(12): add(o+6.0+k*0.115,tick(0.35))
for k in range(7): add(o+6.3+k*0.42,pop())
for j in range(16): add(o+10.35+j*0.04+0.08,flip())
add(o+11.2,whoosh(0.5,1.0)); add(o+11.4,thud(0.9)); add(o+11.9,ding()); add(o+12.4,pop())
sfx=sfx[:N]; sfx/=np.max(np.abs(sfx)); mix=0.13*bed+0.22*sfx; mix/=max(1,np.max(np.abs(mix))/0.9)
aw=work/'audio.wav'; ww=wave.open(str(aw),'w'); ww.setnchannels(1); ww.setsampwidth(2); ww.setframerate(sr); ww.writeframes((mix*32767).astype(np.int16).tobytes()); ww.close()
an=work/'audio_n.wav'
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(aw),'-af','acompressor=threshold=-30dB:ratio=4:attack=3:release=120,loudnorm=I=-18:TP=-1.5:LRA=9','-ar','48000','-ac','2',str(an)],check=True)
subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','30','-i',str(fr/'f%05d.jpg'),'-i',str(an),'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',str(out)],check=True)
print('done',out,T)
