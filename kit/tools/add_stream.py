"""TikTok version: append the 'daily live stream' end card (kit/cta/stream.html, 6 s) to a finished video.
Usage: python3 add_stream.py in.mp4 out_tiktok.mp4   (Instagram uses the video without this card)"""
import sys, pathlib, wave, subprocess, numpy as np
from playwright.sync_api import sync_playwright
src=pathlib.Path(sys.argv[1]).resolve(); out=pathlib.Path(sys.argv[2]).resolve()
KIT=pathlib.Path(__file__).resolve().parent.parent
work=out.parent/('work_stream_'+out.stem); fr=work/'frames'; fr.mkdir(parents=True,exist_ok=True)
for f in fr.glob('*.jpg'): f.unlink()
fps=30; T=6.0
with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  pg=b.new_page(viewport={'width':1080,'height':1920}); pg.goto((KIT/'cta'/'stream.html').as_uri()); pg.wait_for_timeout(800)
  for i in range(int(T*fps)):
    pg.evaluate(f'render({i/fps})'); pg.screenshot(path=str(fr/f'f{i:05d}.jpg'),type='jpeg',quality=92)
  b.close()
sr=48000; N=int(T*sr); tt=np.arange(N)/sr; rng=np.random.default_rng(11)
br=np.cumsum(rng.standard_normal(N)); br-=np.convolve(br,np.ones(4800)/4800,mode='same'); br/=np.max(np.abs(br))
pad=sum(np.sin(2*np.pi*f*tt)*(0.6+0.4*np.sin(2*np.pi*0.2*tt+j)) for j,f in enumerate([110,164.81,220.0,277.18])); pad/=np.max(np.abs(pad))
bed=(0.5*br+0.5*pad)*np.minimum(1,np.minimum(tt/0.4,(T-tt)/1.5))
def env(m,a,d):
  e=np.ones(m); ai=max(1,int(a*sr)); e[:ai]=np.linspace(0,1,ai); e*=np.exp(-np.arange(m)/(d*sr)); return e
def whoosh(dur=0.45,g=1.4):
  m=int(dur*sr); nz=rng.standard_normal(m); y=np.zeros(m); a=np.linspace(0.02,0.25,m); v=0
  for i in range(m): v+=a[i]*(nz[i]-v); y[i]=v
  return y*np.sin(np.linspace(0,np.pi,m))**2*g
def thud(g=1.0,d=0.12): m=int(0.5*sr); f=np.linspace(120,42,m); return np.sin(2*np.pi*np.cumsum(f)/sr)*env(m,0.002,d)*g
def pop(g=0.8): m=int(0.12*sr); f=np.linspace(900,500,m); return np.sin(2*np.pi*np.cumsum(f)/sr)*env(m,0.003,0.03)*g
def tick(g=0.35): m=int(0.04*sr); x=np.arange(m)/sr; return np.sin(2*np.pi*2400*x)*env(m,0.001,0.006)*g
def ding(g=0.5,f0=1320): m=int(1.2*sr); x=np.arange(m)/sr; return (np.sin(2*np.pi*f0*x)+0.5*np.sin(2*np.pi*2*f0*x)+0.25*np.sin(2*np.pi*1.5*f0*x))*env(m,0.002,0.3)*g
sfx=np.zeros(N+2*sr)
def add(t,s): i=int(t*sr); sfx[i:i+len(s)]+=s
add(0.0,whoosh(0.5)); add(0.15,thud(1.1)); add(0.55,pop()); add(0.85,pop())
for k in range(11): add(1.15+k*0.055,tick())
add(1.75,thud(1.3,0.18)); add(1.78,ding()); add(1.85,pop()); add(2.3,pop(0.6)); add(2.6,pop(0.6))
sfx=sfx[:N]; sfx/=np.max(np.abs(sfx)); mix=0.13*bed+0.22*sfx; mix/=max(1,np.max(np.abs(mix))/0.9)
aw=work/'a.wav'; w=wave.open(str(aw),'w'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((mix*32767).astype(np.int16).tobytes()); w.close()
an=work/'a_n.wav'; seg=work/'seg.mp4'
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(aw),'-af','acompressor=threshold=-30dB:ratio=4:attack=3:release=120,loudnorm=I=-18:TP=-1.5:LRA=9','-ar','48000','-ac','2',str(an)],check=True)
subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','30','-i',str(fr/'f%05d.jpg'),'-i',str(an),'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-shortest',str(seg)],check=True)
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(src),'-i',str(seg),'-filter_complex','[0:v]fps=30,format=yuv420p[v0];[1:v]fps=30,format=yuv420p[v1];[0:a]aresample=48000,aformat=channel_layouts=stereo[a0];[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]','-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)],check=True)
print('done',out)
