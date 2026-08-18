Vercel deployment notes for Akhgam Herbals

Required Environment Variables (set in Vercel Project > Settings > Environment Variables):

- SECRET_KEY: Flask secret key
- MYSQL_HOST: Hostname or IP of your MySQL instance
- MYSQL_USER: MySQL username
- MYSQL_PASSWORD: MySQL password
- MYSQL_DB: MySQL database name (default: akhgam_herbals)

Mail / SMTP (if using email features):
- MAIL_SERVER
- MAIL_PORT
- MAIL_USERNAME
- MAIL_PASSWORD
- MAIL_DEFAULT_SENDER (optional)

Razorpay (if using payments):
- RAZORPAY_KEY_ID
- RAZORPAY_KEY_SECRET
- RAZORPAY_WEBHOOK_SECRET

Other recommended env vars:
- SITE_NAME, SITE_EMAIL, SITE_PHONE, WHATSAPP_NUMBER (optional overrides)

Notes about persistent uploads:
- The app writes uploaded media to `static/uploads/...` (configured by `UPLOAD_FOLDER` in `config.py`). Vercel serverless functions have an ephemeral filesystem; files written to disk will not persist across deployments or instance restarts.
- Recommended approaches for persistent uploads:
  1. Store uploads in an S3 bucket (or other object storage). Use AWS S3, DigitalOcean Spaces, or any S3-compatible storage.
  2. Configure the app to upload files directly to S3 and serve media from the bucket or a CDN.
  3. Alternatively, host uploads on a separate VM/container with persistent disk and point the app to that storage.

Minimal S3 integration suggestions (no code changes performed):
- Create an S3 bucket and an IAM user with PutObject/GetObject permissions.
- Add these env vars to Vercel:
  - S3_BUCKET_NAME
  - S3_ACCESS_KEY_ID
  - S3_SECRET_ACCESS_KEY
  - S3_REGION
- Option A (recommended): Update upload routes to send files to S3 instead of `UPLOAD_FOLDER`.
- Option B: Keep current uploads but run a background process to sync `static/uploads` to S3 (not reliable on serverless).

Vercel deployment steps:
1. Commit & push the repo with `vercel.json` and `api/index.py` added.
2. Connect your GitHub repo in the Vercel dashboard and create a new Project.
3. In Vercel Project Settings, add the environment variables listed above.
4. Deploy (Vercel will use Python 3.12 as configured in `vercel.json`).

Local testing:
- Install dependencies:
```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```
- Run Vercel dev (requires Node + Vercel CLI):
```bash
npm i -g vercel
vercel dev
```

If you want, I can:
- Add example S3 upload code and configuration (requires changes to app upload routes).
- Add a small `upload_adapter.py` helper that keeps the app logic isolated.

