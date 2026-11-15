#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <openssl/sha.h>
#define M 24435180ULL
#define MS 12
#define MO 40
typedef struct{int id; uint64_t tg; int ns; int no[MS]; char *s[MS][MO]; int sl[MS][MO];} D;
static int perm[MS], ch[MS], found; static D *cur; static long tests;
static int dfs(int lv, SHA256_CTX *c){
  int si=perm[lv];
  for(int o=0;o<cur->no[si];o++){
    SHA256_CTX x=*c; SHA256_Update(&x,cur->s[si][o],cur->sl[si][o]);
    if(lv==cur->ns-1){ SHA256_Update(&x,".",1); unsigned char d[32]; SHA256_Final(d,&x); tests++;
      uint64_t v=0; for(int q=0;q<8;q++) v=(v<<8)|d[q];
      if(v%M==cur->tg){ ch[si]=o; return 1; } }
    else { SHA256_Update(&x,". ",2); if(dfs(lv+1,&x)){ ch[si]=o; return 1; } }
  }
  return 0;
}
static int nextp(int *a,int n){ int i=n-2; while(i>=0&&a[i]>=a[i+1]) i--; if(i<0) return 0; int j=n-1; while(a[j]<=a[i]) j--; int t=a[i];a[i]=a[j];a[j]=t; for(int l=i+1,r=n-1;l<r;l++,r--){t=a[l];a[l]=a[r];a[r]=t;} return 1; }
int main(int argc,char**argv){
  int part=atoi(argv[1]), np=atoi(argv[2]); FILE*f=fopen(argv[3],"r"); char buf[2048]; int idx=0;
  while(1){ D d; if(fscanf(f,"%d %lu %d\n",&d.id,&d.tg,&d.ns)!=3) break;
    for(int s=0;s<d.ns;s++){ if(fscanf(f,"%d\n",&d.no[s])!=1) return 1; for(int o=0;o<d.no[s];o++){ if(!fgets(buf,sizeof buf,f)) return 1; int l=strlen(buf); if(buf[l-1]=='\n') buf[--l]=0; d.s[s][o]=strdup(buf); d.sl[s][o]=l; } }
    if(idx++%np!=part){ continue; }
    cur=&d; int ok=0; for(int i=0;i<d.ns;i++) perm[i]=i;
    do{ SHA256_CTX c; SHA256_Init(&c);
        for(int o=0;o<d.no[0] && !ok;o++){ SHA256_CTX x=c; SHA256_Update(&x,d.s[0][o],d.sl[0][o]); SHA256_Update(&x,". ",2); if(dfs(1,&x)){ ch[0]=o; ok=1; } }
        if(ok) break;
    } while(nextp(perm+1,d.ns-1));
    if(ok){ printf("%d",d.id); for(int i=0;i<d.ns;i++) printf(" %d",perm[i]); printf(" |"); for(int i=0;i<d.ns;i++) printf(" %d",ch[i]); printf("\n"); }
    else printf("%d MISS\n",d.id);
    fflush(stdout);
  }
  fprintf(stderr,"part %d done, tests %ld\n",part,tests);
}
