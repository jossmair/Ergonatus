"""Monotonic countdown independent of display refresh frequency."""
import math,time

class Countdown:
    def __init__(self,clock=time.monotonic):
        self.clock=clock;self.work=300;self.rest=300;self.cycle=False;self.phase='Travail';self.state='ready';self.deadline=None;self.left=300
    def configure(self,work,rest=300,cycle=False):
        if not 1<=work<=5999 or (cycle and not 1<=rest<=5999):raise ValueError('Choisissez une durée entre 00:01 et 99:59.')
        self.work=work;self.rest=rest if 1<=rest<=5999 else 300;self.cycle=cycle;self.reset()
    @property
    def duration(self):return self.rest if self.phase=='Pause' else self.work
    def remaining(self):return max(0,self.deadline-self.clock()) if self.state=='running' else self.left
    def start(self):self.phase='Travail';self.left=self.work;self.deadline=self.clock()+self.work;self.state='running'
    def pause(self):
        if self.state=='running':
            changed=self.tick()
            if self.state=='running':self.left=self.remaining();self.deadline=None;self.state='paused'
            return changed
        return False
    def resume(self):
        if self.state=='paused':self.deadline=self.clock()+self.left;self.state='running'
    def reset(self):self.phase='Travail';self.left=self.work;self.deadline=None;self.state='ready'
    def tick(self):
        if self.state!='running' or self.remaining()>0:return False
        if not self.cycle:self.left=0;self.deadline=None;self.state='finished';return True
        now=self.clock();period=self.work+self.rest
        self.deadline+=math.floor((now-self.deadline)/period)*period
        while self.deadline<=now:
            self.phase='Pause' if self.phase=='Travail' else 'Travail';self.deadline+=self.duration
        return True

def time_text(seconds):
    seconds=max(0,math.ceil(seconds));return f'{seconds//60:02}:{seconds%60:02}'
