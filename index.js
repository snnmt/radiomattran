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

// KHỞI TẠO FIRESTORE DATABASE
const db = admin.firestore();

app.get("/", (_req, res) => res.json({ service: "radio-mat-tran-api", ok: true }));

function apiKeyAuth(req, res, next) {
  const hdr = req.headers.authorization || "";
  const SERVER_API_KEY = process.env.SERVER_API_KEY || "MAT_KHAU_CUA_STREAMLIT_123"; 
  if (hdr === `Bearer ${SERVER_API_KEY}`) return next();
  return res.status(401).json({ error: "Sai API Key." });
}

// API BẮN THÔNG BÁO
app.post("/admin/sendNotification", apiKeyAuth, async (req, res) => {
  try {
    const { title, body } = req.body;
    if (!title || !body) return res.status(400).json({ error: "Thiếu dữ liệu" });

    const message = {
      topic: "ALL",
      notification: {
        title: title,
        body: body
      },
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

// ====================================================================
// API MỚI: NHẬN DỮ LIỆU LƯỢT XEM TỪ APP ANDROID
app.post("/track", async (req, res) => {
    try {
        const { postId, postTitle, deviceModel, osVersion } = req.body;
        // Lấy IP thật của người dùng
        const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress || "Unknown";

        // Lưu vào bảng "views"
        await db.collection("views").add({
            postId: postId || 0,
            postTitle: postTitle || "Không rõ",
            deviceModel: deviceModel || "Unknown",
            osVersion: osVersion || "Unknown",
            ipAddress: ip,
            timestamp: admin.firestore.FieldValue.serverTimestamp() // Giờ chuẩn server
        });
        
        return res.json({ success: true });
    } catch (e) {
        return res.status(500).json({ error: "Lỗi ghi log", details: String(e) });
    }
});

// API MỚI: TRẢ BÁO CÁO THỐNG KÊ CHO TRANG QUẢN TRỊ
app.get("/admin/stats", apiKeyAuth, async (req, res) => {
    try {
        const snapshot = await db.collection("views").orderBy("timestamp", "desc").limit(1000).get();
        const data = snapshot.docs.map(doc => {
            const item = doc.data();
            if (item.timestamp) {
                // Đổi timestamp thành giờ VN
                item.timeStr = item.timestamp.toDate().toLocaleString("vi-VN", {timeZone: "Asia/Ho_Chi_Minh"});
            } else {
                item.timeStr = "Đang xử lý...";
            }
            return item;
        });
        return res.json(data);
    } catch (e) {
        return res.status(500).json({ error: "Lỗi lấy data", details: String(e) });
    }
});
// ====================================================================

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`API đang chạy trên port ${PORT}`));
