/* Nuxel S10+ kernel-primitive probe.  AArch64, freestanding (no libc).
 *
 * Purpose: measure, on the real handset, which of the kernel primitives
 * systemd's process-spawning path needs actually exist on this 4.14.253 Samsung
 * kernel.  Every result is written to /dev/kmsg so it survives with no usable
 * console (this device's /dev/console open()s to ENODEV).
 *
 * This is a MEASUREMENT, not a fix.  It exists so that the systemd
 * "Failed to spawn executor: Function not implemented" failure is attributed to
 * a specific syscall with a specific errno instead of to a version number.
 *
 * Output lines: "NUXEL-SYSCALL <name> ret=<n> errno=<e> <verdict>"
 */
typedef unsigned long u64;
typedef unsigned int u32;

#define SYS_write   64
#define SYS_exit    93
#define SYS_exit_group 94
#define SYS_waitid  95
#define SYS_clone   220
#define SYS_execve  221
#define SYS_wait4   260
#define SYS_memfd_create 279
#define SYS_pidfd_send_signal 424
#define SYS_open_tree 428
#define SYS_move_mount 429
#define SYS_fsopen  430
#define SYS_fsconfig 431
#define SYS_fsmount 432
#define SYS_fspick  433
#define SYS_pidfd_open 434
#define SYS_clone3  435
#define SYS_openat  56
#define SYS_close   57
#define SYS_getpid  172
#define SYS_uname   160

#define P_PIDFD 3
#define P_PID   1
#define WEXITED 4
#define WNOHANG 1
#define CLONE_PIDFD 0x00001000UL
#define CLONE_VM    0x00000100UL
#define SIGCHLD     17

static long sys0(long n){register long x0 __asm__("x0")=0,x8 __asm__("x8")=n;__asm__ volatile("svc #0":"+r"(x0):"r"(x8):"memory");return x0;}
static long sys1(long n,long a){register long x0 __asm__("x0")=a,x8 __asm__("x8")=n;__asm__ volatile("svc #0":"+r"(x0):"r"(x8):"memory");return x0;}
static long sys2(long n,long a,long b){register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x8 __asm__("x8")=n;__asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x8):"memory");return x0;}
static long sys3(long n,long a,long b,long c){register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x8 __asm__("x8")=n;__asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x8):"memory");return x0;}
static long sys4(long n,long a,long b,long c,long d){register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x8 __asm__("x8")=n;__asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x8):"memory");return x0;}
static long sys5(long n,long a,long b,long c,long d,long e){register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x4 __asm__("x4")=e,x8 __asm__("x8")=n;__asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x8):"memory");return x0;}

/* --- minimal output ------------------------------------------------------- */
static int kfd = -1;
static unsigned long slen(const char *s){unsigned long n=0;while(s[n])n++;return n;}
static void raw(int fd,const char *s,unsigned long n){
    if(fd>=0 && sys3(SYS_write,fd,(long)s,n)==(long)n) return;
    sys3(SYS_write,2,(long)s,n);   /* fall back to stderr -> /dev/kmsg (init.sh exec 2>/dev/kmsg) */
}
static void put(const char *s){ raw(kfd,s,slen(s)); }
static void putsfd(int fd,const char *s){ raw(fd,s,slen(s)); }
static void dec(long v){
    char b[24]; int i=0; unsigned long u;
    if(v<0){ put("-"); u=(unsigned long)(-v); } else u=(unsigned long)v;
    if(!u){ put("0"); return; }
    while(u && i<(int)sizeof b){ b[i++]=(char)('0'+(u%10)); u/=10; }
    while(i--) { char c=b[i]; raw(kfd,&c,1); }
}
static void hex(unsigned long v){
    static const char *h="0123456789abcdef"; char b[19]; int i;
    put("0x"); for(i=0;i<16;i++) b[i]=h[(v>>((15-i)*4))&0xf];
    for(i=0;i<16;i++) raw(kfd,&b[i],1);
}
/* one result line: NUXEL-SYSCALL <name> ret=<v> errno=<e> <verdict> */
static void rep(const char *name,long r,const char *verdict){
    put("NUXEL-SYSCALL "); put(name); put(" ret="); dec(r);
    put(r<0?" errno=":" rc="); dec(r<0?-r:r); put(" ");
    put(r<0&&(-r)==38?"ENOSYS ":(r<0?"(err) ":"(ok) "));
    put(verdict ? verdict : ""); put("\n");
}
static void notef(const char *name,long r,const char *note){
    put("NUXEL-SYSCALL-NOTE "); put(name); put(" ret="); dec(r);
    put(r<0?" errno=":" rc="); dec(r<0?-r:r); put(" "); put(note); put("\n");
}

/* a waitid(P_PIDFD) probe identical in shape to glibc's __clone_pidfd_supported():
   a valid-but-never-allocated fd.  glibc treats ANYTHING but EBADF (9) as
   "pidfd not supported" and makes pidfd_spawn() return ENOSYS. */
static void probe_waitid(void){
    register long x0 __asm__("x0")=P_PIDFD;
    register long x1 __asm__("x1")=0x7fffffc0L;
    register long x2 __asm__("x2")=0;
    register long x3 __asm__("x3")=(WEXITED|WNOHANG);
    register long x8 __asm__("x8")=SYS_waitid;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x8):"memory");
    rep("waitid(P_PIDFD,0x7fffffc0,NULL,WEXITED|WNOHANG)",x0,
        x0==-9?"(EBADF => glibc would accept pidfd_spawn)"
              :"(NOT EBADF => glibc __clone_pidfd_supported()==false, pidfd_spawn()==ENOSYS)");
}
static void probe_waitid_pid(void){
    register long x0 __asm__("x0")=P_PID;
    register long x1 __asm__("x1")=1;         /* PID 1 always exists */
    register long x2 __asm__("x2")=0;
    register long x3 __asm__("x3")=(WEXITED|WNOHANG);
    register long x8 __asm__("x8")=SYS_waitid;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x8):"memory");
    rep("waitid(P_PID,1,NULL,WEXITED|WNOHANG)",x0,x0==-10?"(ECHILD ok)":"(unexpected)");
}
static void probe_clone3(void){
    unsigned long a[11];
    for(int i=0;i<11;i++) a[i]=0;
    /* clone_args: flags,pidfd,child_tid,parent_tid,exit_signal,stack,stack_size,... */
    a[0]=SIGCHLD;
    long r=sys2(SYS_clone3,(long)a,88);
    rep("clone3(args,88)",r,r==-38?"(ENOSYS: clone3 requires Linux 5.3)":"");
}
static void probe_pidfd_open(void){
    long r=sys2(SYS_pidfd_open,1,0);
    rep("pidfd_open(1,0)",r,r==-38?"(ENOSYS: pidfd_open requires Linux 5.3)":"");
}
static void probe_clone_pidfd(void){
    long r=sys5(SYS_clone,CLONE_PIDFD|SIGCHLD,0,0,0,0);
    if(r==0){ sys1(SYS_exit,0); for(;;){} }
    if(r>0){ long st=0; sys4(SYS_wait4,r,(long)&st,(int)0,0); }
    rep("clone(CLONE_PIDFD|SIGCHLD)",r,r<0?"(CLONE_PIDFD requires Linux 5.2)":"(ok)");
}
/* the primitive systemd *actually* needs: plain clone() + execve() */
static void probe_fork_exec(void){
    static const char *argv[]={"sh","-c","exit 7",0};
    static const char *envp[]={"PATH=/bin:/sbin:/usr/bin:/usr/sbin",0};
    long r=sys5(SYS_clone,SIGCHLD,0,0,0,0);
    if(r==0){ sys3(SYS_execve,(long)"/bin/sh",(long)argv,(long)envp); sys1(SYS_exit,127); for(;;){} }
    if(r<0){ rep("clone(SIGCHLD)+execve(/bin/sh)",r,"(FAILED)"); return; }
    int st=0; long w=sys4(SYS_wait4,r,(long)&st,0,0);
    if(w<0){ rep("clone(SIGCHLD)+execve(/bin/sh)",w,"(wait4 FAILED)"); return; }
    long code=(st>>8)&0xff;
    put("NUXEL-SYSCALL clone(SIGCHLD)+execve(/bin/sh) ret="); dec(code);
    put(" errno=0 "); put(code==7?"(ok: child ran /bin/sh and exited 7)\n":"(unexpected child status)\n");
}
static void probe_fsopen(void){
    long r=sys2(SYS_fsopen,(long)"tmpfs",0);
    if(r>=0) sys1(SYS_close,r);
    rep("fsopen(\"tmpfs\",0)",r,r==-38?"(ENOSYS: fsopen requires Linux 5.2 -- explains systemd's tmpfs usrquota probe failing)":"");
}
static void probe_fspick(void){
    long r=sys2(SYS_fspick,(long)"/",0);
    if(r>=0) sys1(SYS_close,r);
    rep("fspick(\"/\",0)",r,r==-38?"(ENOSYS: fspick requires Linux 5.2)":"");
}
static void probe_open_tree(void){
    long r=sys3(SYS_open_tree,-100,(long)"/",0); /* AT_FDCWD, no flags */
    if(r>=0) sys1(SYS_close,r);
    rep("open_tree(AT_FDCWD,\"/\",0)",r,r==-38?"(ENOSYS: open_tree requires Linux 5.2)":"");
}
static void probe_memfd(void){
    long r=sys3(SYS_memfd_create,(long)"nuxel",0,0);
    if(r>=0) sys1(SYS_close,r);
    rep("memfd_create(\"nuxel\",0)",r,r==-38?"(ENOSYS)":"(ok: systemd serialization works)");
}
static void probe_mounts(void){
    /* Can this kernel even give us a cgroup2 superblock?  systemd 258 requires it. */
    long r=sys2(SYS_fsopen,(long)"cgroup2",0);
    if(r>=0) sys1(SYS_close,r);
    notef("fsopen(\"cgroup2\")",r,"(informational: cgroup2 support)");
}

/* freestanding: the compiler may still emit these */
void *memset(void *d,int c,u64 n){volatile unsigned char *p=d;while(n--)*p++=(unsigned char)c;return d;}
void *memcpy(void *d,const void *s,u64 n){volatile unsigned char *p=d;const unsigned char *q=s;while(n--)*p++=*q++;return d;}

void _start(void){
    kfd = (int)sys4(SYS_openat,-100,(long)"/dev/kmsg",1/*O_WRONLY*/,0);
    put("\nNUXEL-SYSCALL-PROBE begin (kernel primitives used by systemd 258)\n");
    probe_waitid();
    probe_waitid_pid();
    probe_clone3();
    probe_pidfd_open();
    probe_clone_pidfd();
    probe_fork_exec();
    probe_fsopen();
    probe_fspick();
    probe_open_tree();
    probe_memfd();
    probe_mounts();
    put("NUXEL-SYSCALL-PROBE end\n");
    put("NUXEL_MARKER SYSCALL_PROBE_DONE\n");
    sys1(SYS_exit_group,0);
    for(;;){}
}
