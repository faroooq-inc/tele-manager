# Telegram Manager Backend (Sketchware Pro)

دا د یو مالک/یو شخصي اکاونټ لپاره د ازمایښتي Backend پروژه ده. دا پروژه دوه برخې لري:

1. **MTProto / Telethon:** د شخصي اکاونټ ننوتل، د چټونو لېست، د پیغامونو لوستل او لېږل.
2. **Telegram Bot API:** د Bot Token تصدیق، د بوټ له لارې پیغام لېږل او د بوټ Updates لوستل.

## مهم امنیتي خبرداری
- `API_ID` او `API_HASH` یوازې د Render Environment Variables کې واچوئ.
- `APP_API_KEY` یو اوږد تصادفي راز وټاکئ او یوازې خپل Android اپ ته یې ورکړئ.
- د Telegram د ننوتلو کوډ، 2FA پاسورډ، Bot Token او Session له چا سره مه شریکوئ.
- هېڅکله `.env` یا `.session` فایل GitHub ته مه پورته کوئ.
- دا نسخه د یوه مالک لپاره ده، نه د عامو خلکو لپاره.
- د شخصي اکاونټ له لارې د پیغامونو لوستل/لېږل د Telegram د اصولو او د اکاونټ د اجازو تابع دي.

## Render کې Deploy

1. دا ZIP خلاص کړئ او ټول فایلونه GitHub ته په نوي Repository کې Upload کړئ.
2. په Render کې `New +` -> `Web Service` وټاکئ او خپل GitHub Repository وصل کړئ.
3. Runtime: Python
4. Build Command:
   `pip install -r requirements.txt`
5. Start Command:
   `uvicorn app:app --host 0.0.0.0 --port $PORT`
6. Environment Variables جوړ کړئ:
   - `TELEGRAM_API_ID` = د my.telegram.org عددې API ID
   - `TELEGRAM_API_HASH` = د my.telegram.org API Hash
   - `APP_API_KEY` = یو اوږد، تصادفي او پټ کیلي
   - `SESSION_PATH` = `/var/data/telegram_manager`
7. د Telegram Session د ساتلو لپاره Persistent Disk د `/var/data` په Mount Path سره ونښلوئ. که Disk نه وي، د سرور د بیا پیل/بدلون پر مهال Session له منځه تللی شي.
8. Deploy وکړئ او `/health` خلاص کړئ.

یادونه: د Persistent Disk لګښت لري او د Render د پلان له شرایطو سره تړلی دی. وړیا/ephemeral خدمت د تلپاتې MTProto Session لپاره د باور وړ نه دی.

## API امنیت
له `/health` پرته هر endpoint د HTTP Header دا غواړي:

`X-API-Key: YOUR_APP_API_KEY`

## مهم Endpoints

### روغتیا
`GET /health`

### د Telegram د ننوتلو کوډ غوښتل
`POST /auth/send-code`
```json
{"phone":"+937XXXXXXXX"}
```

### د کوډ تایید
`POST /auth/verify-code`
```json
{"code":"12345"}
```

که `needs_2fa_password: true` راشي، لاندې endpoint وکاروئ.

### د 2FA تایید
`POST /auth/verify-2fa`
```json
{"password":"YOUR_TELEGRAM_2FA_PASSWORD"}
```

### د ننوتلو حالت
`GET /auth/status`

### د چټونو لېست
`GET /dialogs?limit=30`

### د یوه چټ پیغامونه
`GET /messages?peer=CHAT_ID&limit=30`

### د شخصي اکاونټ له لارې پیغام لېږل
`POST /messages/send`
```json
{"peer":"CHAT_ID","message":"Hello"}
```

### د Bot Token تصدیق
`POST /bot/validate`
```json
{"token":"123456:ABC..."}
```

### د بوټ له لارې پیغام لېږل
`POST /bot/send-message`
```json
{"token":"123456:ABC...","chat_id":"CHAT_ID","text":"Hello"}
```

### د بوټ Updates
`POST /bot/updates`
```json
{"token":"123456:ABC...","limit":20}
```

## د Android / Sketchware Pro سره نښلول
- د سرور HTTPS Base URL وکاروئ.
- په هر درخواست کې `X-API-Key` Header ورزیات کړئ.
- د HTTP غوښتنې په Background Thread کې اجرا کړئ؛ په UI/Main Thread کې شبکه مه چلوئ.
- د API Key او Bot Token په عامه GitHub کوډ یا APK کې مه لیکئ. د عامه APK دننه ساتل شوی API Key بشپړ خوندي نه وي؛ د واقعي عامه اپ لپاره د کاروونکو جلا authentication او rate limiting ته اړتیا ده.

## محدودیتونه
- د Telegram login code hash په حافظه کې ساتل کېږي؛ که سرور د login په منځ کې restart شي، login flow بیا پیل کړئ.
- د Telethon Session په Persistent Disk کې ساتل کېږي.
- د Bot API `getUpdates` او Webhook یو وخت په یوه بوټ کې ګډ مه کاروئ.
- د Bot API له لارې ټول شخصي اکاونټ چټونه نه شي لوستل کېدای.
- د بوټ د جوړولو او مالکیت انتقال کار د BotFather له لارې کېږي؛ دا Backend یې نه کوي.
- دا د کار وړ بنسټیز Backend دی، خو د production عامه خدمت لپاره لا هم باید HTTPS، rate limiting، audit logs، د مالک authentication، او د رازونو مدیریت پیاوړی شي.
