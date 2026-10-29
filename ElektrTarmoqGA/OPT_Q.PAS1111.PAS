 Program Opt_Q;
 "Elektr tarmoqlarining rejimlarini tugunlarning reaktiv quvvatlari bo'yicha optimallashtirish dasturi" 
  uses crt;
      type Massiv=array[1..35] of real;
      type Massiv1=array[1..55] of real;
      type Massiv2=array[1..10] of real;
      type Intmassiv=array[1..35] of integer;
      type Matrix1=array[1..27,1..27] of real;
      type Matrix2=array[1..55,1..55] of real;
 var
 u,d,v1,d1,r,x,at1,at2,bl,bt,vt,bsh,p,q :             Massiv;
                                     pi :             Massiv1;
           dq,al1,al2,qmin,qmax,alu,duc :             Massiv2;
                                 g,b,dd :             Matrix1;
                                  w1,w2 :             Matrix2;
     name,name1,tex,tex1,tex2,tex3,tex4 :             string[15];
                          ib,io,nuf,npl :             intmassiv;
i,j,ii,jj,k,kk,kkk,t,i1,j1,nog,mv,op,qb :             integer;
    nuz,mvt,m5,mm5,nn,nnu,nnu1,n7,n4,nv :             integer;
                                  ch,pf :             char;
                   file_read,file_write :             text;
a,aa,a1,a2,a3,a4,aa1,a11,a22,b1,b2,b3,b4,ui1,ui2,
uj1,uj2,uk1,uk2,du1,du2,pb,qb1,po,qo,dp,dp1,dq1,ddp,
ddq,gg,ppl,alfa,beta,qk,p6,q6,u3,du,ub1 :             real;
ubu,dbu,eps,g11,b11,z,z22,g1,s,s1,s2,s3,s4,s5,s6,
s7,s8,s11,s12,da1,da2,zn,aluu,ab,al,dpl :             real;
Label 2,7,8,9,17,18,19,38,39,40,42,43,46,47,48,51,65,66,67,68,
      83,90,91,92,99;

     {  Y-matritsasini shakllantirish  }
     Procedure FormY;
     Label 38,39;
     begin
      for i:=1 to nuz+1 do
      begin
        for j:=1 to nuz+1 do
        begin
          g[i,j]:=0;
          if i=j then goto 38;
          b[i,j]:=0;
          goto 39;
38:       b[i,i]:=bsh[i];
39:     end;
      end;
      for k:=1 to mvt do
      begin
        i:=ib[k];
        j:=io[k];
        z22:=r[k]*r[k]+x[k]*x[k];
        g11:=r[k]/z22;
        b11:=-x[k]/z22;
        g[i,j]:=at1[k]*g11-at2[k]*b11;
        b[i,j]:=at1[k]*b11+at2[k]*g11;
        g[j,i]:=at1[k]*g11+at2[k]*b11;
        b[j,i]:=at1[k]*b11-at2[k]*g11;
        g[i,i]:=g[i,i]+g11;
        b[i,i]:=b[i,i]+b11+bl[k]/2;
        a22:=at1[k]*at1[k]+at2[k]*at2[k];
        g[j,j]:=g[j,j]+a22*g11;
        b[j,j]:=b[j,j]+a22*b11+bl[k]/2;
      end;
    end;

  { Yakobi matritsasi elementlarini va Chiziqli Algebraik Tenglamalar Tizimi (ChAT) ning o'ng tomonini hisoblash  }
    Procedure Jakobi;
    Label 42,43,46,47,48;
    begin
        nn:=2*nuz;
      	for  i:=1 to nn do
          begin
            for  j:=1 to nn+1 do
            w1[i,j]:=0;
          end;
         for  i:=1 to nuz do
         begin
          w1[i,nn+1]:=-g[i,i]*u[i]*u[i]-p[i];
          i1:=i+nuz;
          w1[i1,nn+1]:=b[i,i]*u[i]*u[i]-q[i];
         end;
         for  k:=1 to mvt do
         begin
           i:=ib[k];
           j:=io[k];
           dd[i,j]:=d[i]-d[j];
           a1:=g[i,j]*cos(dd[i,j])+b[i,j]*sin(dd[i,j]);
           a2:=g[i,j]*sin(dd[i,j])-b[i,j]*cos(dd[i,j]);
           a3:=g[j,i]*cos(-dd[i,j])+b[j,i]*sin(-dd[i,j]);
           a4:=g[j,i]*sin(-dd[i,j])-b[j,i]*cos(-dd[i,j]);
           if i=nuz+1 then goto 42;
           w1[i,nn+1]:=w1[i,nn+1]+u[i]*u[j]*a1;
           nnu:=nuz+i;
           w1[nnu,nn+1]:=w1[nnu,nn+1]+u[i]*u[j]*a2;
42:        if j=nuz+1 then goto 43;
           w1[j,nn+1]:=w1[j,nn+1]+u[j]*u[i]*a3;
           nnu:=nuz+j;
           w1[nnu,nn+1]:=w1[nnu,nn+1]+u[j]*u[i]*a4;
43:        if i=nuz+1 then goto 47;
           if j=nuz+1 then goto 46;
           w1[i,j]:=u[i]*u[j]*a2;
           w1[j,i]:=u[j]*u[i]*a4;
           nnu:=j+nuz;
           w1[nnu,i]:=-u[j]*u[i]*a3;
           nnu1:=i+nuz;
           w1[nnu,nnu1]:=u[j]*a4;
           w1[i,nnu]:=u[i]*a1;
           nnu:=i+nuz;
           w1[nnu,j]:=-u[j]*u[i]*a3;
           nnu1:=j+nuz;
           w1[nnu, nnu1]:=u[i]*a2;
           w1[j,nnu]:=u[j]*a3;
46:        if w1[i,i]<>0 then goto 47;
           w1[i,i]:=b[i,i]*u[i]*u[i]-q[i];
           nnu:=i+nuz;
           w1[i,nnu]:=-g[i,i]*u[i]+p[i]/u[i];
           w1[nnu,i]:=g[i,i]*u[i]*u[i]+p[i];
           w1[nnu,nnu]:=b[i,i]*u[i]+q[i]/u[i];
           if j=nuz+1 then goto 48;
47:        if w1[j,j]<>0 then goto 48;
           w1[j,j]:=b[j,j]*u[j]*u[j]-q[j];
           nnu:=j+nuz;
           w1[j,nnu]:=-g[j,j]*u[j]+p[j]/u[j];
           w1[nnu,j]:=g[j,j]*u[j]*u[j]+p[j];
           w1[nnu,nnu]:=b[j,j]*u[j]+q[j]/u[j];
48:      end;
      end;

   {   Chiziqli Algebraik Tenglamalar Tizimini (ChAT) yechish   }
      Procedure ReshUr;
      begin
         n7:=2*nuz;
     for i:=1 to n7 do
     begin
         for j:=i+1 to n7+1 do
         w1[i,j]:=w1[i,j]/w1[i,i];
         for k:=i+1 to n7 do
         begin
           for t:=i+1 to n7+1 do
           w1[k,t]:=w1[k,t]-w1[k,i]*w1[i,t];
         end;
     end;
           for j:=1 to n7-1 do
           begin
             jj:=n7-j;
             aa1:=0;
               for k:=jj+1 to n7 do
               aa1:=aa1+w1[jj,k]*w1[k,n7+1];
             w1[jj,n7+1]:=w1[jj,n7+1]-aa1;
           end;
      end;

   {  Keyingi ichki iteratsiyada o'zgaruvchilarning qiymatlarini hisoblash va natijani chiqarish }
    Procedure IterVivod;
    begin
         for i:=1 to nuz do
         begin
           d[i]:=d[i]-w1[i,nn+1];
           nnu:=i+nuz;
           u[i]:=u[i]-w1[nnu,nn+1];
         end;
     {  Natijalarni chiqarish }
   	  writeln('  Iteratsiya = ',m5:3);
        for i:=1 to nuz do
        writeln(' ',i:3,'   ',u[i]:4:4,'   ', d[i]:4:4,'   ',p[i]:4:4,'   ', q[i]:4:4);

    end;

  {  Oqimlarni va quvvat yo'qotishlarini hisoblash }
      Procedure PerPoter;
      begin
          writeln(Shoxobchalar (liniyalar) bo'yicha quvvat oqimlari);
          ddp:=0; ddq:=0;
          for k:=1 to mvt do
            begin
            i:=ib[k];
            j:=io[k];
            ui1:=u[i]*cos(d[i]);
            ui2:=u[i]*sin(d[i]);
            uj1:=u[j]*cos(d[j]);
            uj2:=u[j]*sin(d[j]);
            uk1:=at1[k]*uj1-at2[k]*uj2;
            uk2:=at1[k]*uj2+at2[k]*uj1;
            du1:=ui1-uk1;
            du2:=ui2-uk2;
            z22:=r[k]*r[k]+x[k]*x[k];
            a1:=(du1*r[k]+du2*x[k])/z22;
            a2:=(-du1*x[k]+du2*r[k])/z22;
            pb:=ui1*a1+ui2*a2;
            qb1:=ui2*a1-ui1*a2;
            po:=uk1*a1+uk2*a2;
            qo:=uk2*a1-uk1*a2;
            dp1:=pb-po;
            dq1:=qb1-qo;
            ddp:=ddp+dp1;
            ddq:=ddq+dq1;
 	  writeln(' ',i:2,'-',j:2,'   ',pb:4:3,'   ',qb1:4:3,'   ',po:4:3,'     ',qo:4:3,'   ',dp1:4:3);
          end;
        writeln('  Umumiy quvvat yo'qotishlari = ',ddp:4:4,'  ',ddq:4:4);
      end;

   {   Elektr energiya tizimining (EET) barqarorlashgan (o'rnatilgan) rejimini hisoblash  }
     Procedure RUR;
     Label 40,51;
     begin
     	m5:=0;
40:   for i:=1 to nuz+1 do
	begin
	  v1[i]:=u[i];
	  d1[i]:=d[i];
	  for j:=1 to nuz+1 do
          dd[i,j]:=d[i]-d[j];
	end;
	n4:=n7+1;

 { Yakobi matritsasi elementlarini va Chiziqli Algebraik Tenglamalar Tizimi (ChAT) ning o'ng tomonini hisoblash rotsedurasiga/funksiyasiga murojaat qilish}
        Jakobi;

 {Chiziqli Algebraik Tenglamalar Tizimini (ChAT) yechish protsedurasiga/funksiyasiga murojaat qilish }
        ReshUr;

	m5:=m5+1;
  {  Keyingi ichki iteratsiyada o'zgaruvchilar qiymatlarini hisoblash va natijani chiqarish protsedurasiga/funksiyasiga murojaat qilish  }
        IterVivod;

  {  Iterativ jarayonning konvergensiyasini tekshirish   }
         aa:=0;
         for i:=1 to nn do
         begin
           if abs(w1[i,nn+1])<=eps then goto 51;
           aa:=aa+1;
51:      end;
        if aa<>0 then goto 40;

  {  Quvvat oqimlari va yo'qotishlarini hisoblash protsedurasiga/funksiyasiga murojaat qilish }
        PerPoter;
     end;

   { Tugun quvvatlari bo'yicha maqsad funksiyasining hosilalarini hisoblash}
    Procedure Proizv;
    Label 67,68;
    begin
   { Yakobi matritsasi elementlarini hisoblash protsedurasiga/funksiyasiga murojaat qilish }
	Jakobi;
	for i:=1 to nn do
	begin
          for j:=1 to nn do
          w1[i,j]:=-w1[i,j];
	end;
   { Chiziqli Algebraik Tenglamalar Tizimi (ChAT) ning balanslovchi (Slack) tuguniga bog'liq bo'lgan o'ng tomon komponentlarini hisoblash }
	for k:=1 to mvt do
	begin
	  j:=io[k];
	  if ib[k]=nuz+1 then goto 67;
	  if io[k]<>nuz+1 then goto 68;
	  j:=ib[k];
67:	  i:=j+nuz{-uz[j]};
	  pi[j]:=-u[nuz+1]*u[j]*(g[j,nuz+1]*sin(-d[j])-b[j,nuz+1]*cos(-d[j]));
	  pi[i]:=-u[nuz+1]*(g[j,nuz+1]*cos(-d[j])+b[j,nuz+1]*sin(-d[j]));
68:	end;
	for i:=1 to nn do
	begin
	  for j:=1 to nuz do
	  pi[i]:=pi[i]+w1[j,i];
	end;
	for i:=1 to nn do
	begin
	  for j:=1 to nn do
	  w2[I,j]:=w1[I,j];
	end;
	for i:=1 to nn do
	begin
	  for j:=i to nn do
	  begin
	    a:=w1[i,j];
	    w1[i,j]:=w1[j,i];
	    w1[j,i]:=a;
	  end;
	end;
	for i:=1 to nn do
	w1[i,nn+1]:=-pi[i];

  {Chiziqli Algebraik Tenglamalar Tizimini (ChAT) yechish protsedurasiga/funksiyasiga murojaat qilish}
	ReshUr
    end;

   { Yangi iteratsiyada tugunlarning optimal reaktiv quvvatlarini hisoblash}
    Procedure OptQ;
    Label 83,90,91,92,94;
    begin
         for i:=1 to qb do
         begin
           j:=nuf[i];
           du:=w1[nuz+j,nn+1];
           aluu:=alu[i];
           if mm5=1 then goto 90;
           if du*duc[i]>0 then goto 91;
           alu[i]:=0.4*alu[i];
           goto 90;
91:        alu[i]:=1.3*alu[i];
90:	   duc[i]:=du;
	   q[j]:=q[j]-alu[i]*du;
	   if q[j]>=qmin[i] then goto 92;
	   q[j]:=qmin[i];
	   alu[i]:=aluu;
	   goto 83;
92:	   if q[j]<=qmax[i] then goto 83;
	   q[j]:=qmax[i];
	   alu[i]:=aluu;
83:        writeln('  ',i:3,'  ',j:3,'  ',alu[i],'  ',q[j]:5:5);
         end;
      end;

  { Elektr tarmog'ining rejimini tugunlarning reaktiv quvvatlari bo'yicha optimallashtirish }
   Procedure Opt;
   Label 17,18,19,65,66;
   begin
  	if qb=0 then goto 65;
	writeln('  Q (reaktiv quvvat) uchun dempferlovchi koeffitsientni kiritish ');
	readln(aluu);
	for i:=1 to qb do
        alu[i]:=aluu;
65:	mm5:=0;
66:	writeln('Tashqi iteratsiya = ',mm5:3,');
	if qb=0 then goto 17;
	for i:=1 to qb do
	begin
	  j:=nuf[i];
	  writeln('  ',j:3,'    ',q[j]:5:5);
 	end;

17: { Elektr tarmog'ining barqarorlashgan rejimini hisoblash protsedurasiga/funksiyasiga murojaat qilish}
	RUR;

	if mm5=0 then goto 18;
	if abs(dp-ddp)<=eps then goto 19;
18:	mm5:=mm5+1;
	dp:=ddp;

   { Tugun quvvatlari bo'yicha maqsad funksiyasining hosilalarini hisoblash protsedurasiga/funksiyasiga murojaat qilish }
       Proizv;

       if qb=0 then goto 66;
   { Yangi iteratsiyada tugunlarning optimal kuchlanishlarini hisoblash protsedurasiga/funksiyasiga murojaat qilish}
       OptQ;

       goto 66;
19: end;

        {  ASOSIY DASTUR  }
   begin
    clrscr;
    writeln;
    name:='DATA_Q.txt';
    assign(file_read,name);
    reset(file_read);
          readln(file_read,tex);
         readln(file_read,tex1);
         readln(file_read,nuz,mvt,ubu,dbu,eps);
	   mv:=0;
         readln(file_read,tex2);
         for k:= 1 to mvt do
	   begin
           readln(file_read,ib[k],io[k],r[k],x[k],at1[k],at2[k],bl[k],bt[k]);
           end;
         k:=0; ub1:=0; qb:=0; nv:=0; j:=0;
         readln(file_read,tex3);
         for i:=1 to nuz do
         begin
           readln(file_read,i,p[i],q[i],u[i],d[i],bsh[i],vt[i]);
	     if vt[i]=0 then goto 2;
	     j:=j+1;
           qb:=qb+1;
           nv:=nv+1;
	   nuf[j]:=i;
2:      end;
	u[nuz+1]:=ubu;
	d[nuz+1]:=dbu;
         if nv=0 then goto 7;
         readln(file_read,tex4);
	 for i:=1 to nv do
         readln(file_read, qmin[i],qmax[i]);
7:     close(file_read);
     writeln('  ',nuz:3,'  ',mvt:3,'  ',ubu:4:4,'  ',dbu:4:5,'  ',eps:2:4);
     writeln;
       for k:=1 to mvt do
  writeln('  ',ib[k]:2,'-',io[k]:2,'  ',r[k]:3:3,'  ',x[k]:3:3,'  ',at1[k]:3:3,'  ',at2[k]:3:3,'  ',bl[k]:3:3,'  ',bt[k]);
     writeln;
       for i:=1 to nuz do
  writeln('  ',i:3,'  ',p[i]:4:4,'  ',q[i]:4:4,'  ',u[i]:4:4,'  ',d[i]:2:5,'  ',bsh[i]:4:6,'  ',vt[i]:2:1);
    n7:=2*nuz;

  { Xususiy va o'zaro o'tkazuvchanliklar (admittanslar) matritsasini shakllantirish protsedurasiga/funksiyasiga murojaat qilish" }
	 FormY;

         writeln('    Elektr energiya tizimining (EET) barqarorlashgan (o'rnatilgan) rejimini hisoblash');
	   writeln('  Optimallashtirishsiz - 0"');
	   writeln('  Optimallashtirish bilan - 1');
	   readln(op);
	   if op<>0 then goto 8;

      { Elektr energiya tizimining (EET) barqarorlashgan rejimini hisoblash protsedurasiga murojaat }
	   RUR;
	   goto 9;

8:    { Elektr tarmog'i rejimini optimallashtirish protsedurasiga murojaat }
	   Opt;

9:	writeln('      Hisoblash natijalarini saqlash uchun fayl nomini kiriting" degan ma'noni anglatadi.

');
	readln(name1);
    	assign(file_write,name1);
    	rewrite(file_write);
	if op=0 then goto 99;
	writeln(file_write);
	writeln(file_write,'   Elektr tarmog'i rejimini optimallashtirish natijasi ');
	writeln(file_write,'   Tashqi iteratsiyalar soni  =  ',mm5:3);
	if qb=0 then goto 99;
	writeln(file_write);
	writeln(file_write,'    Tugunlarning optimal reaktiv quvvatlari');
	writeln(file_write,'      Delta Q, MVAr');
	for i:=1 to qb do
	begin
          j:=nuf[i];
	  writeln(file_write,'     ',j:3,'          ',q[j]:5:5);
        end;
99:  	writeln(file_write);
	writeln(file_write,'  Tugunlarning kuchlanishlari, fazaviy burchaklari, aktiv va reaktiv quvvatlari');
	writeln(file_write,'  ?U, kV; ?d, rad.; ?P, MVt; ?Q, MVAr');
      	for i:=1 to nuz do
      	writeln(file_write,'  ',i:3,'     ',u[i]:4:4,'      ', d[i]:4:4,'      ',p[i]:4:4,'      ', q[i]:4:4);
	writeln(file_write);
      	writeln(file_write,'  Umumiy quvvat yo'qotishlari =   ',ddp:4:4,'    ',ddq:4:4);
	close(file_write);
     end.


