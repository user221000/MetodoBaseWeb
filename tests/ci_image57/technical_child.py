"""Closed19-input source successor; original12 authorities remain unchanged.

The complete reviewed child is authenticated before an exact inverse recovers
the published f690 parent. That inverse certifies only the historical source;
the current native build/probe/SCA have their own mandatory checks.
"""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path
import zlib

SCHEMA = "current57-technical-close-20261103-source-child-v1"
SOURCE_BASIS = 'f69058f49d61d50a6370e05eb607ebe1b4d862df'
NATIVE_PREFIX = 'runtime-source/technical-close-20261103/'
ACTIVE_CONTRACT = NATIVE_PREFIX + "container-contract.json"
ACTIVE_SOURCE_PINS = NATIVE_PREFIX + "source-pins.json"
PARENT_PINS = {'Dockerfile': {'bytes': 26772, 'raw_sha256': '601f9953e0c78c46181899de402b6fb04cf3a6bc4515e0c3122ee719dca317c5', 'git_blob': 'b909b444872af0d73b1aca9a04c1166ecb10a514'}, 'requirements-container-apt-metadata.lock': {'bytes': 661, 'raw_sha256': '6619c1cee5ec9f4efac52d4b12f18d091a4280ed43bcca184293b9ee1f9f91c4', 'git_blob': '4713f16fe41154b967894585ca148a34a60f4424'}, 'requirements-container-bootstrap.lock': {'bytes': 240, 'raw_sha256': '01cb7092ff6e66c2d52618b2076234ca877f833c067c6c3b51fd8607cebc15aa', 'git_blob': '7fdaeecd5c2df604efe6c5227e590a5bffeb8267'}, 'requirements-container-build.lock': {'bytes': 179, 'raw_sha256': 'f51592f81ddb5d3ccf8e01c7b226bde1d1def49e207ce46a8fab488075ff3638', 'git_blob': '378ed67a8a2ed00d3c6d67b70ec7fd6a60817eaf'}, 'requirements-container-psycopg.lock': {'bytes': 169, 'raw_sha256': 'a9d2e085a0958d9b9b1907e6b737de57fd41e6c19749a5068a3182c10e033921', 'git_blob': 'd3776016a2f7350ed4a03750e22589ad1413929e'}, 'runtime-source/expat-sec10/.gitattributes': {'bytes': 8, 'raw_sha256': '705fd4d6451a31d36b3df7de96f83f30ac976c9b4a6d1e51671d8e2f33e2d0da', 'git_blob': 'fa1385d99a319b43c06f5309d1aae9fdd3adea46'}, 'runtime-source/expat-sec10/13c5f63.patch': {'bytes': 528, 'raw_sha256': 'c6c65ee12b494dac2b74e4abb1281a535bb701fcc81880254f13cb77d7a3c2aa', 'git_blob': '9a751a75c3e6f3f33c93ffb9a1c7079384381c21'}, 'runtime-source/expat-sec10/CONTRATO.md': {'bytes': 6041, 'raw_sha256': '31d5f685f5e4550f4a4c351cc65e96f0c4ea12a6ae314ce5fc3c68901a8cb4a1', 'git_blob': 'dedf2f906670289e5a43519b0f5578b2341af08f'}, 'runtime-source/expat-sec10/rebuild_pyexpat.py': {'bytes': 15034, 'raw_sha256': 'ce57c205ea22e8756c47640e1da5acd9d9aa54da1873e6b53d22379a3ec60cab', 'git_blob': '22a45ac9792ebd13fbe55809a1fb7f44f71804b5'}, 'runtime-source/expat-sec10/source-pins.json': {'bytes': 1078, 'raw_sha256': '3e1b837516f2bf5f127c56f79f603db4bfe963983d99283e850a185659ffe4bd', 'git_blob': '3e50fcd80275a7a3c2b8ca70dd03ddcf23d61c72'}, 'requirements-container.lock': {'bytes': 130271, 'raw_sha256': 'a5964eaf6febb9499c5daf5ff1abbdcab51e734c42e23e1c5db5e3e39343571a', 'git_blob': '30ad11eb2e2e83f2090b4fdd1c3ac89a11938865'}, 'runtime-source/container37-contract.json': {'bytes': 2087, 'raw_sha256': '56c9c97bb3fcb8b8f56db3157f844a55a4fe133d82b271a2ae870bbf95918ef5', 'git_blob': '585adab2db383ae0a757446c8ec3fdcb91a1ef41'}}
PINS = {'Dockerfile': {'bytes': 19328, 'raw_sha256': 'eeac19a8ddd5ac2a3e118a83581484ae34e7e3c8d10324015439f94a02b0a8b3', 'git_blob': 'bc0c29afad72e61bccb353256b2fb5b60a080fe1'}, 'requirements-container-apt-metadata.lock': {'bytes': 661, 'raw_sha256': '6619c1cee5ec9f4efac52d4b12f18d091a4280ed43bcca184293b9ee1f9f91c4', 'git_blob': '4713f16fe41154b967894585ca148a34a60f4424'}, 'requirements-container-bootstrap.lock': {'bytes': 240, 'raw_sha256': '01cb7092ff6e66c2d52618b2076234ca877f833c067c6c3b51fd8607cebc15aa', 'git_blob': '7fdaeecd5c2df604efe6c5227e590a5bffeb8267'}, 'requirements-container-build.lock': {'bytes': 179, 'raw_sha256': 'f51592f81ddb5d3ccf8e01c7b226bde1d1def49e207ce46a8fab488075ff3638', 'git_blob': '378ed67a8a2ed00d3c6d67b70ec7fd6a60817eaf'}, 'requirements-container-psycopg.lock': {'bytes': 169, 'raw_sha256': 'a9d2e085a0958d9b9b1907e6b737de57fd41e6c19749a5068a3182c10e033921', 'git_blob': 'd3776016a2f7350ed4a03750e22589ad1413929e'}, 'runtime-source/expat-sec10/.gitattributes': {'bytes': 8, 'raw_sha256': '705fd4d6451a31d36b3df7de96f83f30ac976c9b4a6d1e51671d8e2f33e2d0da', 'git_blob': 'fa1385d99a319b43c06f5309d1aae9fdd3adea46'}, 'runtime-source/expat-sec10/13c5f63.patch': {'bytes': 528, 'raw_sha256': 'c6c65ee12b494dac2b74e4abb1281a535bb701fcc81880254f13cb77d7a3c2aa', 'git_blob': '9a751a75c3e6f3f33c93ffb9a1c7079384381c21'}, 'runtime-source/expat-sec10/CONTRATO.md': {'bytes': 6041, 'raw_sha256': '31d5f685f5e4550f4a4c351cc65e96f0c4ea12a6ae314ce5fc3c68901a8cb4a1', 'git_blob': 'dedf2f906670289e5a43519b0f5578b2341af08f'}, 'runtime-source/expat-sec10/rebuild_pyexpat.py': {'bytes': 15034, 'raw_sha256': 'ce57c205ea22e8756c47640e1da5acd9d9aa54da1873e6b53d22379a3ec60cab', 'git_blob': '22a45ac9792ebd13fbe55809a1fb7f44f71804b5'}, 'runtime-source/expat-sec10/source-pins.json': {'bytes': 1078, 'raw_sha256': '3e1b837516f2bf5f127c56f79f603db4bfe963983d99283e850a185659ffe4bd', 'git_blob': '3e50fcd80275a7a3c2b8ca70dd03ddcf23d61c72'}, 'requirements-container.lock': {'bytes': 130271, 'raw_sha256': '746747a9bb93cf5e995879594c43b64bce77ce66b614c06b927e1448be4cd3e7', 'git_blob': '25c1bdbea2bdcb5d1eca6de4d30cd6cea9693028'}, 'runtime-source/container37-contract.json': {'bytes': 2087, 'raw_sha256': '56c9c97bb3fcb8b8f56db3157f844a55a4fe133d82b271a2ae870bbf95918ef5', 'git_blob': '585adab2db383ae0a757446c8ec3fdcb91a1ef41'}, 'requirements_web.lock': {'bytes': 136089, 'raw_sha256': '9cb932c897d520d9891bfcb2372d04d8283d25e93e01decd6d8a9f573f79bb93', 'git_blob': '123207af498d501daa3380bb47965a3726895b1f'}, 'runtime-source/technical-close-20261103/apt-inputs.json': {'bytes': 6683, 'raw_sha256': '73538a8152aa7f3a707ada1463282e5816010daf24f73172c166ad4c1fb90aa1', 'git_blob': '08fed34cb48a267b4ab9eca65a5cdf5715f54694'}, 'runtime-source/technical-close-20261103/apt-metadata.lock': {'bytes': 506, 'raw_sha256': '6304333abab4b38f69d709b7e862098efea7da3ee888246ea49d67aadd4143ee', 'git_blob': '88e18458079762b67e4dd7a447969e2fbcc0ffc3'}, 'runtime-source/technical-close-20261103/container-contract.json': {'bytes': 2611, 'raw_sha256': '7171e62cee9ad96f1a078105197c482276ed9dc441aeb9cbe2565af734e287e9', 'git_blob': 'cee19f234db38233bc8ea6635a810e674fac0655'}, 'runtime-source/technical-close-20261103/rebuild_native.py': {'bytes': 20599, 'raw_sha256': 'e1926aa14d7c0911f6c1ecc0a283529b51de56ff4cf5f60af40348170213f658', 'git_blob': '4ce2ec9e715b31298c41a3a0bd4ccc0f5e94e392'}, 'runtime-source/technical-close-20261103/source-pins.json': {'bytes': 48425, 'raw_sha256': '9a1d7bd6be0c171c9b263963381afc3f61b29c8dd04d3dd8142e6bb780983d97', 'git_blob': '5cd395f3f3a74f46fd6936a883a84b91ff303b48'}, 'runtime-source/technical-close-20261103/verify_ca.py': {'bytes': 5117, 'raw_sha256': '8a8002bd552762b98b3b916aa90e2c79f4b6fe3d34bc2d6463cb7748ead0aec4', 'git_blob': 'b09a68fdf08b26937c2ec627519925e81fbc72b3'}}
CHANGED = ('Dockerfile', 'requirements-container.lock', 'requirements_web.lock', 'runtime-source/technical-close-20261103/apt-inputs.json', 'runtime-source/technical-close-20261103/apt-metadata.lock', 'runtime-source/technical-close-20261103/container-contract.json', 'runtime-source/technical-close-20261103/rebuild_native.py', 'runtime-source/technical-close-20261103/source-pins.json', 'runtime-source/technical-close-20261103/verify_ca.py')
PARENT_DOCKER_Z85 = 'c-rke?RMM7mH+(|vuqoZF#+O(1W9?(U0R}To!F9&Bqy6XK0NpsNQg-Q0YFJ~>OFmg{n34rK0@E5PqO#k8GryqQdE+r*)~p&Bw%Ll+?o4*=MH|u{`SBB^DpxMli#p6JdgeOxs!4B6?fU+{`6;d6nh_d8iX^>e9n?I_7|QP{`D^rbU$<=KlGhEX0zCHX3WqGOVKq&A06PE4;k~~h+R9`HP6_Rxd``l7%lF)&fK?pEC|1Ke1|1*%KY$(XSw?1H;BbzmWN7~J6D{!i*V*2z)Qw-l^sX$cIE&k36Fdpd7+cBTka}xG+VM(7DnuBc@g^D>M(qG`S!R?V-1xZ#!2X~ES@2@EaD!|oHUGC;-n7aGnVo6CiLT!`kN}7e9OH>?$8nzH=!4&5&S)ep>d?7ah$US3?YP{6Ou5@r_B;bGbLwp+D}}!0$4Iw9y?z|*t6`LE+VERY^Z740sdf$!lN67He7|j)?fgHe<6-U9y?p+*FXYO)eTkevoP{z3m^C?zvk?MCpn+Hu#L!iKtgYkhWQd0>kfJZz*pD{D40881if-6z2d-SFV0Wju!H~~NWe-q3+MltT{}kKIxyT`ppSfqo6cY`@B`0u2iCyUT;I|8(BOJtS&nNshBdSTXJmTLV90$pfMHrM2sj&G5Vzw3j<_2-Q8Qz+(4BppJ1Z<*$NK=hpG$OKzPcDI{qK_Rl)LYO8|B+kas{hpZk%5;5{8WUhXV`Wa7G-Tg;x>xvDKaNZV4Dz2ILBO7vz&IlB?7K(Z!wMcaE1cH;kNg$!>U>g>j@lIe&Wsf*nSAz?#3yzKNRbn<q^EYx=;q@5DTcyR^HDEbYQBrM&xrFJaJC*7a$Hij#WR;SE>hd-W>0de5%&Jjo8a-7IpF>^ja>(OHettF9a%$9Iv0x@L?nwV^T8hJRpr8s3GR&4G5mER>W*0^18D`^TZC6vSTPsGGXc*Ge2$+^~k^?^!pWC*6u(DY~k&Fw14n&pu;Lk}DuCOo`c1m>wKVa_`_Eix;WKv7@~Y82q<kJSg2fvlVO_pIsgtyrm6=E@>L4%A45dwi7MuFvi|@i!g;w<Jl~}1yg|2@pGQUS(wLZ$TK@|W?*6jbyn-}d|L58WMMCPE)jkkISY`%C=Wfr&X>5Zfcf!lG>aX-&=Y;TuMSmR(Vqgvb#q~?@CVk*S>v}Ykb78!$9|Uyk`^PUYa^#*ZjqVV4Q8{Zsg10W)m#BwNk3!vG=OUk9nW!1EiguXH_$cEeU@b!+|)hS*BpH`#3rK$9krh3fsQnFzwdLWZw`Chs{z{+&nEjL6S_EC%)umj*WCNSlwUXrLvl}MOj!cTsGyZX`6@~jE3#QhIrtHCaA5W(+kMje$%iZDy9Eb5u6)Imz;6Eb`!9t;|I{p5NRWFCY=!PA>}~LXI(RgS2s8z#H%^M<x<INfLdv?Iqdj~xxja2OeLlXJOb^G?m*%ukVAJQ5m&Ye$jWVPxUp$jQw;HELqj8b@Fo|#gg?T%@02R1^`9LXv*-M=W^aJcm=?{eS`GPDalfDJ6S_N1&*x{UPGkUKu!KS8fv$&2<kj8WHCvzOYWT!KD+%!1lo8D&GY~$-?w&`_Te_MOF9G}0OTuzTB=fDDup#_eM=Q`SO<n^4PZ@Mlw24>H*bi;Mbp6(BIlWRTG3r2kC3@yX+`(A(Gm=^T3+{Px@7iV7_6L7z$4}90~{h=H5xv33%zRpeXpe(;X1RXE}=&tYgJWcZknmh8%k!g+i$a06?U})5VKYx32^m;PAcr`}Y1HI?>`U8NYjSK@^EZx^!K6HJv?>dHQIm4de_BB`228P22BfUQ~KqG<71p|1~ufx7TtOej8a7Vh;!)?J08G5?s8G+vGjU1~t@bw{d@JB<-?T^e+;P+i^;QOXw8oJ&CPjC(C!_$)&z`rj}&r8f5cVL<$zlXXuaCO)e&oxX<*8whI>Urof_AJL6@E){|2Ci$l15LLAZNU9OuwjDni_6J*0bl334`3{F=o#EG1E(Lr!ULGa>=_0ScclBKXL`oa8V!xUYmS`0qYbovV8Whz>pOG$_WZEK-L$wh<c8LF`=)0Nyn&<X=5W;G8gRuBXsTIe&l>9b(APZ<zOUzchM{S`?!(UYy*lj4$>sUi0M>2H<B#EN=5+b|0(_+D<nVBM4v`cp0tHlo>ZSQN(I$3)(I`l*MwjPa7o?=?anRCT&r$G?Fd&VbA%I5v-p18O-y0K0!P+3P8>?X}H*RfkcaIgVBQ!o6U%uM1pmjVh$Cni}*7P*sa%Czm2ffBsR7Pu~&(2T3oSckL)>lHox?Il+94-yRT7+4s<c&}#ZvY(32u3V{D7EFL4F&&^`euid^ULEG$A^G8z5OP8s($_-^ylQ{=w5T9gP<<j+ZEZGe;q)7@&j8yH=h)H2Lhffg8-?0Q0q)4Ie>UQXJy~}J@8-ZgkZ?ObY=@q9%!oo_z1LMKU=ADy8(xk=ZiEdEQu=o8tSWF^E;9GXgy{spQlriRoOD5E3z*@^~oDG2qPcd4(hrAH?f&=1O|+_UpOvXxGlGV1VT(R2rH6SyTcl9BYu}~4;&zNIA-o5^1+e@sWXQ#rqSNE`ggcLz~?G}o+7VL^BAoY{Vk>kH^KwYztwOuFAN*)cAHE#wNWHYIKF=jO?W=Vd2f)i*>=)kpH>4@kNRyKMy(8tEBA|0ZT6I5TU+H(9lu9lBBXSR9y@F{?O6x8GUzbjb;6T_uERzo1&t6(F|^HWn^g=Yk_}rCAhoUAqoRYDi@K~derKah;J?Ok=_*n34(J_5$s*5~9|i$WH;`Lw8n9l4NhQ)-7dGQjvDt_jJ_6-d`w#E*z9tq?rzkB%81)^ixGYj12&GsE`j}!BSz|kDl~q*s?%m3}dQWIoye(i<f!sa_F$WMJQF>{ziecFUGu$D`GKf-T!#ZLDxlrs;fMevLhCn}=2_nMmm;@P0&5~J|&%y}ypbc7o5#=p1>1ryJf=kjN$V9tAqbeOm(~kX^AU5E@#}Q}nS9rr|KLAX4wMZTE-XZLQU?<E9-24q_d)H2M1)FIL6jGkd9FGemI^ci&TLWZSKI!e9f+j(&q^Wei<o0Hu?q*!UeL-aXFe5ps#2dS4NNVT%h9JOHn1sebMW$gEsWXrT%MNwb^r=%U`4Otf337x;nuvaO*e-?C0Z9&=#VpTusV3k)f<^nazOIdH`6T2S2fbVC|Guu?_7Ws9fkN;YhUqaSzqZpr3;<RsP`HQT`>o5(mkDTb8qh|Tq(B*$gQ}}|U(sapRiVkYuBWQuDqxDR<-Vp7ogUbrRlF<LytnqdZ&Oww$PYCsE0Rf(@z(?$Og_j5ChUF5ijUNc+mu#S{x|8aon(2eCe(Ip0jP`lB14{C?Ex=UpvQltSuNc&VHFBSQrPz^=K1uajB#&NuxhnyG4BJ!Px%#(c#0Xc!h59M5JWFG0y8x+{77-OYRt92O)NK}K(^Fmd!j3?Ck{t+<ZyOz@%k{1a(<T!%;f=74fV{KbHw~`ywd<=-Zh^)px7Igz>eT3ai$a@S<2@zY_xKtqb|+7IN>;?p6S9A*fVy+BOjiMtp%4Jnlemk!rnD@tW}(ikxO1$n-#xw$_|+Ixz__<?tooz`LrhKQ!?oQM97fz{#T*Kc6d@(@3fx6%&m8+_|Ol-Ckcl^pt4JV<-6YKVE{GLEp>GPXop$f0hl-eHnKLl>W%{ZLTaW-%JEbiTqPh>y4YnW>VzpF-}8J*N(#+9#b~bVy_f!9hfwJH0>?t?rXY1wDRI-4#7*Z;?p@2ypB~}%2)$6~&JDgysbW!6+!t94MM)cgpo<)i8Uh{tFx>>Ks+BOH#*u26O|#`3?8k>zn@Mmgzr)-(Mb<~)%0cT@;k7%n(AlItWMZR$xdR1qieclzXu)^lSir)%13(Tn9=$^6h(vOlg&#TlcbggPbEa!X@AJ=%^<)4cErfbA(qfBMaX?p%t!S>4JO0#N=189QR-GweJc96e{@L2)yDl>o;)EOsJV(3Gm|=-Zqx9#n9aP^984W|&68Y+#{vO%kdnxaYLbw~Bb_P4(MR;K@N?}B?h&aChzpN5IB-a?g?TB`&{1s<dEE1-1q=J%eH9%mdm}{H9IDS28w9CZK)_zCF=MCh+@!So8glOX!Xqq$)vDhNz-x84<yXB%KG;oLXMn~#{2c%;I=WP_24(*&^HE<yoGbgPlB{tv&LQ*9a5?4}cGfpxbT7{9dw2fF?jZMW$*ItQbuf1GTKbz&_HiUhoq^}AlK58}YfTbww1X{svEb?H8w9Ht%$YI6XWghdks=t^gMT92?Y@U^ta0}rQm*^I;?|sj5mhsJ#;^IhmW;0~0QgH(Zg~4)4&8_x>jF73GL#0p129&a{zHP&vQuRx#k^tMf2ZiTeKqy_g8eDP~>u`m3M}55V_k^P*m$^0hMd$d^$Ar!J9=#3Faw3ljf1r%u4tc;EIWITK6Q&LHEN-3WP)-#5d#cl!qF%Dm+O<Dz*}n{tv}=JqF#whmWG%r@HRal2d-C$m&8_|0hv_S+gpGh#2No*$tDuF{`3E#^;vutze?SIv8h;RbvR#fU(0(dm5?ftJQ-|EP=?A_nPz$jrF}IEOR#;-BkT%LV@0N)Q87s@F(GoefzzbX_EYXA*z=1H5VLvP~+YvJp>4-rVk<hbyT2@f4(`f`j&U8w8bvi{mJDqOOtik~AE<vKREHzn{NB-huUO8sU^R1nwdM?HYw?bJvqGO5@!2Vo64l>D7F+`L}D9YCEJIfj-Cr4N#ie-Fd-RhDQQ3|0%IOnpu54Z>XcJK=@d?dXYf(?>IBcMBEEeRF@o`D|0Ebi?!=QH9u0XN48&`Hq05V@4qsm@o>E56N`wElAxD4cj%28ZgC!_%{`3)Z6!N?AIoxDbazVCEz$9mniCNZbp8s5+Fin6o5IV1q-@!ju;%D`~K9#&aM@RzMNJqlB%<qGDNQBQ&Lb07DKW%>Wqe$eprCXJuJkvP?p%rOU#30!Btje}Z)&IZ_TH2l$~(Vi3!of?J0o2TKtW|73FVB|H22^400d(do(MSLer<ljmPwP7Y6xCblkd7VU3Op1*zZVsbt?vh^oVzB)bs0(>*p1+wB?fBW;F;D2^O)zSJvy%btB{xbg;MYrU!jW1Z_V3uEz67WRww5Zla+T^?_ZXKUp5{KUvM^B3k-sUlrHXDnblJAJeQ6yITA?jtvr8fsA7-ALlr6s(;31=DeW-$PK2H;3dVE6@S0G0_bVId9p$4$s@cgqMCr4_ZeKUhre0eMtK)UV~b|NP~;LUyP+uiyvrlkgtFE{3biTrqT0C85x#2WQ|rfSURAO};8FM1K4IBc|!f`jkAoDQ0|Z?Pg`YyXrOT#lkzPiXUG~Tws2`B=x5d@SlBO9;#@q)v<yB7D>mgMXaQN`?fw%bzRY9X{cVTYVV3wfFbHt*8nvi4GBUlGq-xO*jeqX14aLD0nKdwTzpR+WR>j;XUAiWZH1!GSYlIj+T4GlW*cl5cy{*8nY+Hjq60tl@)n*_iSw#f^P9XWLQp!a#ym~ZjoKoNkb!6QWD5Wap|ufitGSY3oQu{aTgo+3LzaQt&9Kx+yvGF7hqi6s(A*z7H>(p%Or6d}B-)%{JcnkNe1k;neO4Z9H|k#a9?I~60^~zcx0Z@rz~qee^#R?*0cIA#rMO%}{z#Y!@0?=3EcDSoNzg9`J;9X%S$U(VP8f7^l57e6uM|r1?e?#+hj1FU^pLQmV}aZ7t7q`5XYi0P{4h0#a3weYYQO*4?e}VeE6=lg2YOF6R87&*lzNup^Bdbxd%B_<(j@nUxu%viV=c`uHLY3RAK(xm7_#Df`w#aWV#<+R#}GAc5f`C)f1JFmCg~D1U=sxNX!Bn+<jEd}T%@x1H|3iJd)=(>TFy^m=>-O5{%gC<UnPic@Gf*W22)<MsY)Klv#jX8t-T8r?EW2-O+RPC>E~K2wEH~ysaB1A_n_x<UwAhQtk92-60G`dt`4A!rTB;uM_ZXXw|4!V3XgPb&@7gPCs3IxX1k6v*iBkw!Mxp(-W}>)i#z(r9lFLa;O?lW^}V4t95|*n7z`{+@A($*X+76>N5h^q!0R)*=9nYj@N~Z*r=b|?NYza>cR;p2HajRK;D6edCPclp5<)zo#sYoYHU~q^8j@H0z*Pg=Zu+J*81@3s@EvZA`iAK`J$Eqj03%;_5zC>;hl8PM4F|nI*LA}(f}W2na&^nGAdHfM$}SRZTTr`p+=%Fv5`X#T?CAL1-leLGI+LUE<zzZJJ3V{_R%m4O^j=>xWD@n&_~O;YWO8I{6=pqr@p}C7!fq;88fbQ;r;?;R2=A1+lkA+*R;!NJ4--9+tlwYoszL_u#5@8TruN0ls#Hq*j;T#W!CN0#octlPcao?!4WUSQRn6uD@>`8devC|h3=<>?8o@X(!r&DeXn5!e3?!J57WPuFX0h99ey-kL&zkMJP>8<3>$)6gi#PAI_hmnNqv9zR7P^4Dg$IYN<{H;3IQ2(c;-~&0OkQBE0u5fx`B6p3<|9_FVM*{w9PzRZ3mU+4Z8cSNkGf4Xk5uRy)#mLssVu0es?E~4L!3^IAX(N3Uw<ToX%BG8La6OEkrykg9TZkIz%xes*KHzK<$~@+z*02HnJ9O{w#8NekKjbM{7y#msQ~!234YK@hRMc}EL_QoKNu%JH?ig|fdGjfMZ22c<v-5E1u5qr(c48kx4}0PFsk!-$({ykZ#k&VTAk)62sbvut|Uk9xpzM@XR_06-fg0v&<9IIN6M)rOMVBsKpfEHX-^VHc*wIzz`^0poK2`1>ju2)CsObvXUb=^Ina@_4;)n_9{51CcLiE-#wM>{h*Kb6#6z=kwnGS;j=Kc|;?|~)SAGVj%3qkXp)s|Ljc`*7n<m;J;?%W!tFN?Ca%L|MKHdce*n-AQ<znz~T9L?tYet8QOyVSu8n-2*(5mdpK?&|se<3HcJ8%?>z;pe0ZrAB|FWf7dSMN7w%^tnnim6?B%8v{f)@}5CTua+~zp1;fx;L+d(j1RECMvC8EiNu}<OW1Oujs~&&7}_7+<KQk0-x@>#@a&U^`mm*01G2nK&s-Gd``Z0V18eWD`)2PO|!IK10XmS%mto>&qVeb^df}mVVu?^hnTjq^QiX)^WZnJy0r}VzWsJi0D`dgxU>5MobZUQwP`B)y{<UBg^KmW>J(Eql)IrdwR#HG1S?n3Le1hGdx4)K@t5=+pM9b2iJLGUtKu%Yn!na3bL08O_hh&fENIx&teajxuuSkXbMJbs4Us!Od8rCRx(0TRiA10x7St)|{bryEu6EL;YT1y3#~Etk!ZcH9hr1M~FjR@b=UAGJCoHs0x7_Wj!X6f5NCCk6Y3+4II^-w+GB*F~U;G9BQGWa{E5H7SpXZ~y5>iBjQ`#+l7cXHk;-`3#rCyhQh({+0yYyp)Ed3CVi#!CwFMrALIY>8x5WmIC0Bjxf6TfI3;2Gf;5>xJBZd-n`5Wl+!_~UZ39E>E$Xp26Mx8xFQ2L9H}iFmQfn-F3RcE;0rnBg8#TD?u?aAg?K%><w03V@~nUpyCX20cjN;z3UE*=I!!9&DoHqid2a0j;?-oK)|sT*sinKnr81)e!GGz6Eo2UbGw(J+S0SOoO}dB@hfRj-Xn@O9pWo#p2VE9IsHvtW}h&i(WiJy*P`PZK}Ph)aSvYEk0yPfwaJ)(tb3)98W0;K_Ahp)@EU0uuXW$x2NZqHh#9T!f$i|B8kH&2Ld>Fh6FDY+VxoK$5j`I*Jz#H+AE@ocRi1N_VjL3`)al^IK^)0Ns@QiJiG$u7S=_d+&p^D%Iu-!QPE!wqfh{@ybwKn5T!EX2;L_3T6_6qqi0-tY34vFy=<Xyc71nb+o&hvbD3oK{211QVRYe;m4*p8K(H6P3DbN5*1cNdsIo60Qdm_{W&jg&)1+Z#-6clW=&{M7OIbRJp~S`ExFaex#R&>TELi17_s3*HCu88yV|Y?tPVg2fmMfcsGQS;0H^i{Z1J)nZ>N9;5v(R1OL)H<_TA>2*iY!L@qJC5AwM^aRzV4H55x+21u=-3S=*AAntKgw}0%n`3!<-0Oep}=bYED2Cn!Gej^6WkoFc+001Zpm4rt<fMMr8C^uV%Y#(*&!!{Y{;dMaqlbh{*2V5;f6V{9WQhNu}~KKxJ+OTW!GSa+HKp-o+{}u~ZsX7rzLcY^Xw9LuIZ?lEeDKq=`ve!%__u>tQMfFv<N{llpvgL5He75a}*K>y&>g0;r0d2oX&XH#>r&Jj!5OY3dcdTI+4yro3Y5H`^s9jWr(~E2sB!AG;W`R1&TGkGi*xy}*<UxnJsCV_CxM{ws6SJAnJ+<Ptpul*vVBo2;UC?4*2)q^=#&E$9nC(+t#8D=Kr7t9+v1ug+$I7nw^T7+cb<MW;lhQfKikPwCQNncAc|6qp2lsm*qkDFsLEA}?}Qano|sq{R(Nx>C7~_hq_M(5T??f@JH@q~D6VDtR}z<(EWw*F1rBHs5#rLPq5cADn5f)|5J-T-=egtM@q`tn=Dx7@M^NUw|LQDfr^yN4_coOF4bOsrgQss_&n|&cp6U?SeMX@G~o5EA8*gp}-pl;`}xe=eM}{Pvv&gCohV1ylYC+Hm$Bz+>LI&Cmuuh$Dx9%eTLXJ8b*2H5+`n#ZzQ7j3Q%o-o8kjJ$mmhAI_W5soDJ4;kx<?Z9>{9TWAw^O+vS1Qt`x2GcVt9Yre!5jDw*^0&QM0n>6ABvWU3r}o0Hmy#NS>_N*5SgUvX!aUkjH&IPl_A?5xYqop5&REGfC__;}Kv$=k6ReVsg8cpkokrHYz*M3SoOJSQT%gpm%DC!OF@yqb((U%ongH97o((sLkfH?ZfXhB>U_@KL8H5^5#EY=SR4z|>T6V@j=e_~xjp`O1$~cG&u{>#if$gKk$h2C4@C=?6{rbp7gT6MgSyhc(gtZsJF}n%!&Kvn~q95}FFkv99!wf5fOVXZn*Tlm9w9y_m4yevc47k(Vhp6bS*rQp%4ga5#+TbKtFK=qKVQ)KF_m8jzQbA=gdlRK58pxb}CA`yPAaJ>79wxU(?3uHW#P^AxWq(DAZ}nLx)ojBX>4f@d>l$y1f#$1_kG=MdlEXX+g{CMsfGSXRFURCtolFbBl*+C3tg2pnD*8)0C4OTfZ8=80$~ak&DPfMKWjVw7N`O3>us1*=sO9h?_R9$?91*{PP<D16~A>x#QD6iL;r=RsBU)}G79RRjGY9x<^bc<=T2<fVP6zP)^*4CSkrXD_E;Oun`Ux;3)2{tL@E9Q1XwZyjm<-q^6lLqnffLv7N3F}6&tUkmuAUrx?1j!#eQ;`{Tp#*0^Dqi@-s;q^>IA6a_fxLV+jMkC*{xaM&$=o`9cIIcMw^}NAoWDEx;cSa*_YL=&Kqh8?m>mlZ2t_R(ZUH>kzZS4+{2u&Xh*()EH{?!Tk)d~953HpEH1j&^?ibfB(MO8A{_B&a<aVutrKZ@DkH|kE%zm!+9=9KL4BmNJ`I8sR'
LOCK_INVERSES = {'requirements-container.lock': {'parent_pin': {'bytes': 130271, 'raw_sha256': 'a5964eaf6febb9499c5daf5ff1abbdcab51e734c42e23e1c5db5e3e39343571a', 'git_blob': '30ad11eb2e2e83f2090b4fdd1c3ac89a11938865'}, 'current_block': b'pyasn1==0.6.5 \\\n    --hash=sha256:4017b0fce125096b8573b39c989fdb1a4b19cf761e683398184550fea0e66587 \\\n    --hash=sha256:6b11616a6bcf3a40e635f082bb232fa57b5e0dd7f517bd7ddd69ec3794508a47\n', 'parent_block': b'pyasn1==0.6.4 \\\n    --hash=sha256:deda9277cfd454080ec40b207fb6df82206a3a2688735233cdcd8d3d565f088b \\\n    --hash=sha256:9c447d8431c947fe4c8febc4ed9e760bc29011a5b01e5c74b67025bd9fb8ce81\n'}, 'requirements_web.lock': {'parent_pin': {'bytes': 136089, 'raw_sha256': '5c0901d887478e24c2762bd29ebb9ef9430aae59ba83ed4c6a6a7d68c05527ec', 'git_blob': 'cc5f24eae0823dec77c84c442f0de219d12ec95c'}, 'current_block': b'pyasn1==0.6.5 \\\n    --hash=sha256:4017b0fce125096b8573b39c989fdb1a4b19cf761e683398184550fea0e66587 \\\n    --hash=sha256:6b11616a6bcf3a40e635f082bb232fa57b5e0dd7f517bd7ddd69ec3794508a47\n', 'parent_block': b'pyasn1==0.6.4 \\\n    --hash=sha256:deda9277cfd454080ec40b207fb6df82206a3a2688735233cdcd8d3d565f088b \\\n    --hash=sha256:9c447d8431c947fe4c8febc4ed9e760bc29011a5b01e5c74b67025bd9fb8ce81\n'}}

def record(raw):
    if type(raw) is not bytes:
        raise ValueError("Exact technical source bytes required")
    return {"bytes": len(raw), "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False).hexdigest()}


def selected(records):
    row = records.get("Dockerfile", {})
    return row.get("raw_sha256") == PINS["Dockerfile"]["raw_sha256"]


def pins(records):
    if not PINS.keys() <= records.keys():
        raise ValueError("All19 technical critical inputs are required")
    native = {name for name in records if name.startswith('runtime-source/')}
    if native != {name for name in PINS if name.startswith('runtime-source/')}:
        raise ValueError("Unreviewed technical native source membership")
    for name, expected in PINS.items():
        row = records[name]
        if type(row.get("bytes")) is not int or any(row.get(key) != value for key, value in expected.items()):
            raise ValueError("Exact technical input identity differs")
    return {name: dict(row) for name, row in PINS.items()}


def inverse(payloads):
    if set(payloads) != set(PINS):
        raise ValueError("Exact19 technical source payloads required")
    pins({name: record(raw) for name, raw in payloads.items()})
    parent = {name: payloads[name] for name in PARENT_PINS}
    parent["Dockerfile"] = zlib.decompress(base64.b85decode(PARENT_DOCKER_Z85))
    for name, change in LOCK_INVERSES.items():
        raw = payloads[name]
        if raw.count(change["current_block"]) != 1:
            raise ValueError("Exact pyasn1 inverse block differs")
        restored = raw.replace(change["current_block"], change["parent_block"], 1)
        if record(restored) != change["parent_pin"]:
            raise ValueError("Lock inverse did not recover the exact parent")
        parent[name] = restored
    if any(record(parent[name]) != pin for name, pin in PARENT_PINS.items()):
        raise ValueError("Technical inverse did not recover the exact production parent")
    return parent


def transition(parent_transition):
    return {"schema": SCHEMA, "source_basis": SOURCE_BASIS,
            "parent_transition": parent_transition, "parent_critical_input_count": 12,
            "critical_input_count": 19, "parent_native_merkle_objects": 21,
            "changed_source_files": list(CHANGED), "changed_parent_input_count": 2,
            "added_critical_input_count": 7, "inherited_parent_inputs": 10,
            "critical_inputs": {name: dict(pin) for name, pin in PINS.items()},
            "parent_inputs": {name: dict(pin) for name, pin in PARENT_PINS.items()},
            "active_contract": ACTIVE_CONTRACT, "active_source_pins": ACTIVE_SOURCE_PINS,
            "python_version": "3.12.16", "expat_version": "2.10.0",
            "scope": "Exact source transition; historical parent authentication only, no build, runtime or SCA acceptance"}


def is_transition(value):
    if type(value) is not dict or value.get("schema") != SCHEMA:
        return False
    from . import context, production_child
    return value == transition(production_child.transition(context.native_transition()))


def input_paths(root):
    from . import authority
    root = Path(root)
    docker = authority.regular_file(root / "Dockerfile").read_bytes()
    return tuple(PINS) if record(docker) == PINS["Dockerfile"] else tuple(PARENT_PINS)


def read_payloads(root):
    from . import authority
    root = Path(root)
    directory = authority.regular_directory(root / NATIVE_PREFIX)
    # The six current inputs occupy one flat namespace. Directories, aliases
    # and ignored descendants cannot hide outside the finite source universe.
    members = {path.relative_to(root).as_posix() for path in directory.iterdir()}
    if members != {name for name in PINS if name.startswith(NATIVE_PREFIX)}:
        raise ValueError("Unreviewed technical native source membership")
    expected = {name for name in PINS if name.startswith('runtime-source/')}
    expected_directories = {str(parent).replace('\\', '/') for name in expected
                            for parent in Path(name).parents if str(parent) not in {'.', 'runtime-source'}}
    actual = {path.relative_to(root).as_posix() for path in (root / 'runtime-source').rglob('*')}
    if actual != expected | expected_directories:
        raise ValueError("Unreviewed runtime source namespace membership")
    payloads = {}
    for name, pin in PINS.items():
        path = authority.regular_file(root / name)
        if path.stat().st_size != pin["bytes"]:
            raise ValueError("Technical input size differs")
        with path.open("rb") as source:
            payloads[name] = source.read(pin["bytes"] + 1)
    pins({name: record(raw) for name, raw in payloads.items()})
    return payloads


def details(root=None):
    root = Path(__file__).resolve().parents[2] if root is None else Path(root)
    payloads = read_payloads(root)
    return json.loads(payloads[ACTIVE_CONTRACT]), json.loads(payloads[ACTIVE_SOURCE_PINS])


def expected_prepared(pins_value):
    prepared = dict(pins_value["psf_selected_sha256"])
    for name, value in pins_value["expat_selected_sha256"].items():
        target = "Modules/expat/" + (name[4:] if name.startswith("lib/") else name)
        if target in prepared:
            raise ValueError("Conflicting exact native source origins")
        prepared[target] = (pins_value["namespace_adaptation"]["after_sha256"]
                            if target == "Modules/expat/expat_external.h" else value)
    if len(prepared) != 45:
        raise ValueError("Exact45 native prepared files required")
    return prepared
