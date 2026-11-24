#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <net/if.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#ifndef SO_BINDTOIFINDEX
#define SO_BINDTOIFINDEX 62
#endif
int main(void) {
    int fd=socket(AF_INET,SOCK_DGRAM,0), index=(int)if_nametoindex("lo");
    assert(fd>=0 && index>0);
    assert(setsockopt(fd,SOL_SOCKET,SO_BINDTOIFINDEX,&index,sizeof index)==0);
    char name[IF_NAMESIZE]={0};socklen_t len=sizeof name;
    assert(getsockopt(fd,SOL_SOCKET,SO_BINDTODEVICE,name,&len)==0 && !strcmp(name,"lo"));
    index=INT_MAX;
    assert(setsockopt(fd,SOL_SOCKET,SO_BINDTOIFINDEX,&index,sizeof index)==-1);
    len=sizeof name;
    assert(getsockopt(fd,SOL_SOCKET,SO_BINDTODEVICE,name,&len)==0 && !strcmp(name,"lo"));
    index=0;
    assert(setsockopt(fd,SOL_SOCKET,SO_BINDTOIFINDEX,&index,sizeof index)==0);
    len=sizeof name;
    assert(getsockopt(fd,SOL_SOCKET,SO_BINDTODEVICE,name,&len)==0 && len==0);
    assert(setsockopt(-1,SOL_SOCKET,SO_BINDTOIFINDEX,&index,sizeof index)==-1 && errno==EBADF);
    close(fd);puts("socket binding compatibility: PASS");return 0;
}
