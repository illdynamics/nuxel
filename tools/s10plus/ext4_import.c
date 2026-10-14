/* Import regular host files into an offline ext4 image using libext2fs.
 * Build: cc -O2 -Wall -o ext4_import ext4_import.c -lext2fs -lcom_err
 * Usage: ext4_import IMAGE HOSTFILE /absolute/destination [mode-octal]
 * NEVER run on a mounted filesystem. For image-building only.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/stat.h>
#include <time.h>
#include <ext2fs/ext2fs.h>
#include <com_err.h>
#define CHECK(x) do{errcode_t err_=(x);if(err_){com_err("ext4_import",err_,"at %s:%d",__FILE__,__LINE__);exit(2);}}while(0)
static ext2_filsys fs;
static ext2_ino_t subdir(ext2_ino_t parent,const char *name){
 ext2_ino_t ino=0; errcode_t e=ext2fs_lookup(fs,parent,name,strlen(name),NULL,&ino);
 if(e==0) return ino;
 CHECK(ext2fs_mkdir(fs,parent,0,name));
 CHECK(ext2fs_lookup(fs,parent,name,strlen(name),NULL,&ino));
 return ino;
}
int main(int argc,char**argv){
 if(argc<4||argc>5||argv[3][0]!='/'){fprintf(stderr,"Usage: %s IMAGE SRC /PATH [MODE]\n",argv[0]);return 1;}
 FILE*in=fopen(argv[2],"rb");if(!in){perror("open source");return 1;}
 unsigned int mode=(argc==5)?strtoul(argv[4],NULL,8):0644;
 CHECK(ext2fs_open(argv[1],EXT2_FLAG_RW,0,0,unix_io_manager,&fs));
 CHECK(ext2fs_read_bitmaps(fs));
 char *path=strdup(argv[3]),*p=path;while(*p=='/')p++;
 ext2_ino_t parent=EXT2_ROOT_INO;
 char *last=strrchr(p,'/');
 if(last){*last=0;char *save=NULL;for(char*part=strtok_r(p,"/",&save);part;part=strtok_r(NULL,"/",&save))parent=subdir(parent,part);p=last+1;}
 ext2_ino_t ino; errcode_t look=ext2fs_lookup(fs,parent,p,strlen(p),NULL,&ino);
 if(look){
  CHECK(ext2fs_new_inode(fs,parent,LINUX_S_IFREG|mode,0,&ino));
  struct ext2_inode inode={0};
  inode.i_mode=LINUX_S_IFREG|mode; inode.i_links_count=1;inode.i_flags=EXT4_EXTENTS_FL;
  inode.i_mtime=inode.i_ctime=inode.i_atime=time(NULL);
  ext2fs_inode_alloc_stats2(fs,ino,1,0);
  CHECK(ext2fs_write_new_inode(fs,ino,&inode));
  CHECK(ext2fs_link(fs,parent,p,ino,EXT2_FT_REG_FILE));
 }else{
  fprintf(stderr,"Refusing to overwrite existing file %s (inode %u)\n",argv[3],ino);return 3;
 }
 ext2_file_t file; CHECK(ext2fs_file_open(fs,ino,EXT2_FILE_WRITE,&file));
 char buf[65536];size_t n;while((n=fread(buf,1,sizeof buf,in))>0){unsigned int written;CHECK(ext2fs_file_write(file,buf,n,&written));if(written!=n){fprintf(stderr,"short write\n");return 2;}}
 CHECK(ext2fs_file_close(file));
 fclose(in); free(path);
 CHECK(ext2fs_flush(fs));CHECK(ext2fs_close(fs));
 printf("Imported %s -> %s\n",argv[2],argv[3]);return 0;
}
