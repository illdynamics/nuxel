/* Remove specific obsolete device paths from an UNMOUNTED ext4 image.
 * Build: cc -O2 -Wall -o ext4_remove ext4_remove.c -lext2fs -lcom_err
 * usage: ext4_remove IMAGE /absolute/path ...
 * Review paths and take a copy of image first. See rootfs-finish.py.
 */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
#include <ext2fs/ext2fs.h>
#include <com_err.h>
#define CHECK(e) do{errcode_t x=(e);if(x){com_err("ext4_remove",x,"line %d",__LINE__);exit(2);}}while(0)
static ext2_filsys fs;
struct item{char *name;ext2_ino_t ino;};
struct entries{struct item *items;unsigned n;};
static int collect(ext2_ino_t dir,int entry,struct ext2_dir_entry *e,int off,int blocksize,char *buf,void *private){
 (void)dir;(void)entry;(void)off;(void)blocksize;(void)buf;
 struct entries*list=private;
 int len=ext2fs_dirent_name_len(e);if(!e->inode||(len==1&&e->name[0]=='.')||(len==2&&!strncmp(e->name,"..",2)))return 0;
 list->items=realloc(list->items,sizeof(struct item)*(list->n+1));
 list->items[list->n].name=strndup(e->name,len);list->items[list->n].ino=e->inode;list->n++;return 0;
}
static void remove_node(ext2_ino_t parent,const char*name,ext2_ino_t ino,int depth){
 if(depth>24){fprintf(stderr,"too deep\n");exit(1);}
 struct ext2_inode inode;CHECK(ext2fs_read_inode(fs,ino,&inode));
 int isdir=LINUX_S_ISDIR(inode.i_mode);
 if(isdir){
  struct entries entries={0};CHECK(ext2fs_dir_iterate2(fs,ino,0,NULL,collect,&entries));
  for(unsigned i=0;i<entries.n;i++){remove_node(ino,entries.items[i].name,entries.items[i].ino,depth+1);free(entries.items[i].name);}free(entries.items);
 }else if(LINUX_S_ISREG(inode.i_mode)){
  ext2_file_t file;CHECK(ext2fs_file_open(fs,ino,EXT2_FILE_WRITE,&file));
  CHECK(ext2fs_file_set_size2(file,0));CHECK(ext2fs_file_close(file));
 }
 CHECK(ext2fs_unlink(fs,parent,name,ino,0));
 if(isdir){struct ext2_inode p;CHECK(ext2fs_read_inode(fs,parent,&p));if(p.i_links_count>2){p.i_links_count--;CHECK(ext2fs_write_inode(fs,parent,&p));}}
 inode.i_links_count=0;inode.i_dtime=(__u32)time(NULL);
 CHECK(ext2fs_write_inode(fs,ino,&inode));
 ext2fs_inode_alloc_stats2(fs,ino,-1,isdir);
 printf("REMOVED %s inode=%u\n",name,ino);
}
int main(int argc,char**argv){
 if(argc<3){fprintf(stderr,"usage: ext4_remove IMAGE /path ...\n");return 1;}
 CHECK(ext2fs_open(argv[1],EXT2_FLAG_RW,0,0,unix_io_manager,&fs));CHECK(ext2fs_read_bitmaps(fs));
 for(int i=2;i<argc;i++){
  char *path=strdup(argv[i]);if(path[0]!='/'){fprintf(stderr,"absolute paths only\n");return 1;}
  char *last=strrchr(path,'/');char *name=last+1;if(!*name)return 1;
  ext2_ino_t parent=EXT2_ROOT_INO,ino=0;
  *last=0;if(*path){CHECK(ext2fs_namei(fs,EXT2_ROOT_INO,EXT2_ROOT_INO,path,&parent));}
  CHECK(ext2fs_lookup(fs,parent,name,strlen(name),NULL,&ino));
  remove_node(parent,name,ino,0);free(path);
 }
 CHECK(ext2fs_flush(fs));CHECK(ext2fs_close(fs));return 0;
}
