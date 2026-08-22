# -*- coding: utf-8 -*-
import struct, sys

def lz4_block_decompress(src, dest_size):
    out=bytearray(); i=0; n=len(src)
    while i<n:
        tok=src[i]; i+=1
        ll=tok>>4
        if ll==15:
            while True:
                b=src[i]; i+=1; ll+=b
                if b!=255: break
        out+=src[i:i+ll]; i+=ll
        if i>=n or len(out)>=dest_size: break
        off=src[i]|(src[i+1]<<8); i+=2
        ml=tok&0x0F
        if ml==15:
            while True:
                b=src[i]; i+=1; ml+=b
                if b!=255: break
        ml+=4
        start=len(out)-off
        for j in range(ml): out.append(out[start+j])
    return bytes(out[:dest_size])

class ARZ:
    def __init__(self, path):
        self.d=open(path,'rb').read()
        (unk,ver,self.rt_start,self.rt_size,self.rt_entries,
         self.st_start,self.st_size)=struct.unpack_from('<hhiiiii',self.d,0)
        self._read_string_table()
        self._read_record_headers()
    def _read_string_table(self):
        p=self.st_start
        cnt=struct.unpack_from('<i',self.d,p)[0]; p+=4
        st=[]
        for _ in range(cnt):
            ln=struct.unpack_from('<i',self.d,p)[0]; p+=4
            st.append(self.d[p:p+ln].decode('latin-1')); p+=ln
        self.st=st
    def _read_record_headers(self):
        p=self.rt_start; hdrs=[]
        for _ in range(self.rt_entries):
            fn=struct.unpack_from('<i',self.d,p)[0]; p+=4
            tl=struct.unpack_from('<i',self.d,p)[0]; p+=4
            typ=self.d[p:p+tl].decode('latin-1'); p+=tl
            off,cs,ds,u1,u2=struct.unpack_from('<iiiii',self.d,p); p+=20
            hdrs.append({'name':self.st[fn],'type':typ,'off':off,'cs':cs,'ds':ds})
        self.hdrs=hdrs
    def record(self, hdr):
        raw=self.d[hdr['off']+24:hdr['off']+24+hdr['cs']]
        dec=lz4_block_decompress(raw, hdr['ds'])
        rec={}; p=0; n=len(dec)
        while p+8<=n:
            typ,cnt=struct.unpack_from('<hh',dec,p); p+=4
            fnidx=struct.unpack_from('<i',dec,p)[0]; p+=4
            fname=self.st[fnidx]
            vals=[]
            for _ in range(cnt):
                if typ==1:
                    vals.append(struct.unpack_from('<f',dec,p)[0])
                elif typ==2:
                    vals.append(self.st[struct.unpack_from('<i',dec,p)[0]])
                else:
                    vals.append(struct.unpack_from('<i',dec,p)[0])
                p+=4
            rec[fname]=vals[0] if cnt==1 else vals
        return rec

if __name__=='__main__':
    import os
    GD=os.environ.get("GD_DIR","C:/games/Steam/steamapps/common/Grim Dawn")
    az=ARZ(f"{GD}/database/database.arz")
    print("records:",len(az.hdrs),"strings:",len(az.st))
    want=['compa_frozenheart','compa_markofthemyrmidon','compa_chilledsteel','compa_sanctifiedbone']
    for hdr in az.hdrs:
        low=hdr['name'].lower()
        if any(w in low for w in want) and 'materia' in low:
            print("\n#####", hdr['name'], " TYPE=",hdr['type'])
            rec=az.record(hdr)
            for k in sorted(rec):
                v=rec[k]
                print(f"   {k} = {v}")
