import os,struct,stat
class Ext4:
 def __init__(self,path,mode='rb'):
  self.f=open(path,mode); self.f.seek(1024); self.sb=self.f.read(1024)
  self.u16=lambda b,o:struct.unpack_from('<H',b,o)[0]
  self.u32=lambda b,o:struct.unpack_from('<I',b,o)[0]
  assert self.u16(self.sb,56)==0xef53
  self.bs=1024<<self.u32(self.sb,24); self.ipg=self.u32(self.sb,40); self.isize=self.u16(self.sb,88) or 128
  self.descsize=self.u16(self.sb,254) or 32
  self.groups_off=2*self.bs if self.bs==1024 else self.bs
  self.file_inodes={}
 def inode(self,ino):
  group=(ino-1)//self.ipg; index=(ino-1)%self.ipg
  self.f.seek(self.groups_off+group*self.descsize); desc=self.f.read(self.descsize)
  tbl=self.u32(desc,8)+(self.u32(desc,40)<<32 if self.descsize>=64 else 0)
  off=tbl*self.bs+index*self.isize
  self.f.seek(off); b=self.f.read(self.isize)
  return b,off
 def blocks(self,ino):
  b,_=self.inode(ino)
  assert (self.u32(b,32)&0x80000),'nonextents not supported'
  def walk(data):
   magic,ents,maximum,depth,gen=struct.unpack_from('<HHHHI',data,0)
   assert magic==0xf30a
   if depth==0:
    for i in range(ents):
     lblock,n,hi,lo=struct.unpack_from('<IHHI',data,12+i*12)
     assert n<=0x8000
     yield lblock,n,lo+(hi<<32)
   else:
    for i in range(ents):
     lblock,lo,hi,_=struct.unpack_from('<IIHH',data,12+i*12)
     self.f.seek((lo+(hi<<32))*self.bs); yield from walk(self.f.read(self.bs))
  return list(walk(b[40:100]))
 def get(self,ino):
  b,_=self.inode(ino); size=self.u32(b,4)+(self.u32(b,108)<<32 if stat.S_ISREG(self.u16(b,0)) else 0)
  if stat.S_ISLNK(self.u16(b,0)) and size<=60 and not (self.u32(b,32)&0x80000):
   return bytes(b[40:40+size])
  ext=self.blocks(ino); data=bytearray(size)
  for lb,n,pb in ext:
   start=lb*self.bs; length=min(n*self.bs,size-start)
   if length>0:
    self.f.seek(pb*self.bs); data[start:start+length]=self.f.read(length)
  return bytes(data)
 def write_same_size(self,ino,data):
  assert 'w' in self.f.mode or '+' in self.f.mode
  original=self.get(ino); assert len(data)==len(original),f'len {len(data)} expected {len(original)}'
  for lb,n,pb in self.blocks(ino):
   start=lb*self.bs; length=min(n*self.bs,len(data)-start)
   if length>0:
    self.f.seek(pb*self.bs); self.f.write(data[start:start+length])
  self.f.flush()
 def children(self,ino):
  data=self.get(ino); result={}
  for offset in range(0,len(data),self.bs):
   block=data[offset:offset+self.bs]; idx=0
   while idx+8<=len(block):
    num,reclen,namelen,t=struct.unpack_from('<IHBB',block,idx)
    if reclen<8 or reclen>len(block)-idx:break
    if num and namelen:
     name=block[idx+8:idx+8+namelen].decode('utf-8','replace')
     if name not in ('.','..'):result[name]=(num,t)
    idx+=reclen
  return result
 def resolve(self,path):
  ino=2
  for s in path.strip('/').split('/'):
   if s:ino=self.children(ino)[s][0]
  return ino
 def tree(self,start=2,path='',depth=0):
  for k,(ino,t) in self.children(start).items():
   name=path+'/'+k
   b,_=self.inode(ino)
   print(name,oct(self.u16(b,0)),self.u32(b,4))
   if stat.S_ISDIR(self.u16(b,0)) and depth<15:self.tree(ino,name,depth+1)
if __name__=='__main__':
 import sys
 fs=Ext4(sys.argv[1]); print('blocksize',fs.bs,'inode size',fs.isize)
 fs.tree()
