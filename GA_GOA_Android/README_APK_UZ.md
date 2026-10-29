# GA–GOA Android APK loyihasi

## Nimalar bor?
- `main.py` — Kivy mobil interfeysi, 4 ta rejim.
- `ga_goa_compare.py` — AC power-flow / GA–GOA hisoblash yadrosi.
- `DATA_Q14.txt` — 13 tugunli, 20 shoxobchali kirish ma'lumoti.
- `buildozer.spec` — Android paketlash sozlamalari.
- `.github/workflows/android-apk.yml` — GitHub Actions orqali APK yig'ish.

## Ilova menyusi
0. Optimallashtirishsiz AC quvvat oqimi
1. Reaktiv quvvat Q ni GA–GOA bilan optimallashtirish
2. Transformator Kre/Kim ni GA–GOA bilan optimallashtirish
3. Q + transformatorlarni GA–GOA bilan optimallashtirish

Natijalar tartibli jadval ko'rinishida chiqadi va ilovaning ichki katalogiga CSV/TXT sifatida saqlanadi.

## APK yig'ish — eng qulay yo'l
Bu muhitda Android SDK/NDK va Buildozer mavjud bo'lmagani uchun APK faylining o'zi bu yerda kompilyatsiya qilinmadi. Loyiha APK yig'ishga tayyorlangan.

1. ZIPni oching.
2. GitHub'da yangi repository yarating va ushbu loyiha fayllarini yuklang.
3. `Actions` bo'limini oching.
4. `Build Android APK` workflow'ini tanlab `Run workflow` ni босинг.
5. Ish tugagach, `ga-goa-debug-apk` artifact'ini yuklab oling. Ichida `app-debug.apk` bo'ladi.

Yoki Linux/WSL muhitida:
```bash
python3 -m pip install --user buildozer cython==0.29.36
buildozer -v android debug
```
APK `bin/` papkasida hosil bo'ladi.

## Muhim
Bu loyiha Android uchun paketlash loyihasi. APK build muvaffaqiyatli tugaganini Android SDK bilan yig'maguncha tasdiqlab bo'lmaydi. Hisoblash yadrosining boshlang'ich natijasi original Pascal natijasi bilan hali to'liq mos emas; mobil ilova hisoblash modelidagi shu farqni avtomatik hal qilmaydi.
