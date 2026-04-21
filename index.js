const express = require("express");
const cors = require("cors");
const admin = require("firebase-admin");
const bodyParser = require("body-parser");

const app = express();
app.use(cors());
app.use(bodyParser.json({ limit: "1mb" }));

if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert({
      projectId: process.env.FIREBASE_PROJECT_ID,
      clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
      privateKey: (process.env.FIREBASE_PRIVATE_KEY || "").replace(/\\n/g, "\n"),
    }),
  });
}

app.get("/", (_req, res) => res.json({ service: "radio-mat-tran-api", ok: true }));

function apiKeyAuth(req, res, next) {
  const hdr = req.headers.authorization || "";
  const SERVER_API_KEY = process.env.SERVER_API_KEY || "MAT_KHAU_CUA_STREAMLIT_123"; 
  if (hdr === `Bearer ${SERVER_API_KEY}`) return next();
  return res.status(401).json({ error: "Sai API Key." });
}

app.post("/admin/sendNotification", apiKeyAuth, async (req, res) => {
  try {
    const { title, body } = req.body;
    if (!title || !body) return res.status(400).json({ error: "Thiếu dữ liệu" });

    const message = {
      topic: "ALL",
      // =========================================================
      // THÊM KHỐI NÀY: Bắt buộc Android tự động hiển thị thông báo
      // =========================================================
      notification: {
        title: title,
        body: body
      },
      // Vẫn giữ khối data để khi bấm vào thông báo app biết đường xử lý
      data: { 
        title: title, 
        body: body, 
        click_action: "OPEN_MAIN_ACTIVITY", 
        docId: String(Date.now()) 
      },
      android: { 
        priority: "high", 
        ttl: 0 
      }
    };

    const response = await admin.messaging().send(message);
    return res.json({ success: true, messageId: response });
  } catch (e) {
    return res.status(500).json({ error: "Lỗi server", details: String(e.message || e) });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`API đang chạy trên port ${PORT}`));
