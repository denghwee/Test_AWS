# Project Answers: FPT Customer Chatbot API

## 1. Database Design

### Vì sao chọn cấu trúc bảng này?

Mình chọn thiết kế database theo mô hình quan hệ chuẩn hóa (3NF) để giảm trùng lặp dữ liệu và dễ quản lý hơn. Các bảng như `Users`, `Tickets`, `Bookings`, và `Conversations` được tách riêng để mỗi bảng chỉ xử lý một chức năng cụ thể.

Ví dụ:
- `Users` lưu thông tin người dùng
- `Tickets` lưu các yêu cầu hỗ trợ
- `Bookings` lưu thông tin đặt lịch
- `Conversations` lưu lịch sử hội thoại

Cách thiết kế này giúp:
- Dễ mở rộng hệ thống
- Dễ query và JOIN dữ liệu
- Hạn chế dữ liệu bị duplicate
- Dễ bảo trì về sau

Ngoài ra:
- `id` kiểu Integer được dùng làm khóa chính nội bộ để tăng tốc độ indexing/query
- `uuid` được dùng cho API public để tránh lộ số lượng dữ liệu trong database

### Trade-off khi dùng Foreign Key cho `user_id`

#### Ưu điểm
- Đảm bảo tính toàn vẹn dữ liệu (Referential Integrity)
- Tránh trường hợp ticket hoặc booking không thuộc user nào
- Hỗ trợ JOIN dữ liệu hiệu quả
- Có thể dùng Cascade Delete để xóa dữ liệu liên quan khi xóa user

#### Nhược điểm
- Insert/Update sẽ chậm hơn một chút vì database phải kiểm tra ràng buộc
- Khó scale theo kiểu distributed/sharding
- Các bảng phụ thuộc nhau nhiều hơn

---

## 2. Authentication

### JWT Token Flow

1. User gửi email/password tới endpoint `/auth/login`
2. Server kiểm tra thông tin đăng nhập trong database
3. Nếu hợp lệ, server tạo JWT Token chứa:
   - `sub`: user_id
   - `exp`: thời gian hết hạn
4. Token được ký bằng `SECRET_KEY`
5. Client lưu token và gửi kèm trong header:

```http
Authorization: Bearer <token>
```

6. Với mỗi request tiếp theo:
   - Server sẽ verify token
   - Nếu token hợp lệ và chưa hết hạn thì cho phép truy cập API

### Security Considerations khi lưu token phía client

#### Local Storage / Session Storage

Ưu điểm:
- Dễ implement

Nhược điểm:
- Dễ bị đánh cắp thông qua XSS (Cross-site Scripting)

#### HttpOnly Cookie

Ưu điểm:
- Javascript không đọc được token
- An toàn hơn trước XSS
- Có thể bật `Secure` để chỉ gửi qua HTTPS

Nhược điểm:
- Có nguy cơ bị CSRF nếu không có CSRF protection

Trong production, mình ưu tiên:
- HttpOnly Cookie
- HTTPS
- CSRF Token

---

## 3. API Design

### Vì sao dùng UUID thay vì Auto Increment ID?

### Ưu điểm

#### Bảo mật hơn
Người dùng không thể dễ dàng đoán ID của tài nguyên khác bằng cách tăng số.

Ví dụ:
- `/tickets/1`
- `/tickets/2`

sẽ dễ bị enumerate hơn so với UUID.

#### Phù hợp với Distributed System
Nhiều service/database khác nhau có thể generate UUID mà không sợ bị trùng.

#### Có thể generate phía client
Client có thể tạo ID trước khi gửi request.

### Nhược điểm

#### Tốn bộ nhớ hơn
UUID dài hơn Integer nên:
- Index lớn hơn
- Query chậm hơn một chút trên dataset lớn

#### Khó debug hơn
UUID khó đọc và khó nhớ hơn số nguyên.

---

## 4. Error Handling

### Implement Rate Limiting như thế nào?

Mình sẽ implement rate limiting bằng:
- FastAPI Middleware
- Hoặc API Gateway như Nginx/Kong

Trong môi trường production có nhiều server:
- Redis sẽ được dùng để lưu số lượng request
- Vì Redis hỗ trợ chia sẻ state giữa nhiều instance

Một số thuật toán phù hợp:
- Fixed Window
- Sliding Window
- Token Bucket

### HTTP Status Code trả về

Khi vượt quá giới hạn request:

```http
429 Too Many Requests
```

Kèm theo header:

```http
Retry-After
```

để client biết cần chờ bao lâu trước khi gửi lại request.

---

## 5. Integration & Deployment

### Deploy API cùng AI Core trong production

### Containerization

Sử dụng Docker để đóng gói:
- FastAPI
- LangChain
- LangGraph
- Các dependencies khác

Dùng multi-stage Dockerfile để:
- Giảm kích thước image
- Tăng bảo mật

### Scaling

Deploy bằng Kubernetes (K8s).

Sử dụng:
- Horizontal Pod Autoscaler (HPA)

để tự động scale pod theo:
- CPU
- RAM
- Request count

Vì AI Core thường tốn tài nguyên:
- Có thể tách AI Core thành microservice riêng
- Giúp scale độc lập với API service

### Monitoring

#### Logging

Sử dụng:
- ELK Stack
  - Elasticsearch
  - Logstash
  - Kibana

Hoặc cloud logging như:
- AWS CloudWatch
- Google Cloud Logging

#### Metrics

Dùng:
- Prometheus để collect metrics
- Grafana để visualize

Theo dõi:
- API latency
- Error rate
- AI inference time
- CPU/RAM usage

#### Distributed Tracing

Sử dụng OpenTelemetry để trace request giữa:
- API Gateway
- FastAPI
- AI Core
- Database

Giúp debug bottleneck dễ hơn trong hệ thống microservices.

---

## 6. Testing & Coverage Strategy

### Vì sao đạt được 92% Coverage?

Để đạt được độ phủ cao và tin cậy, mình áp dụng các chiến lược sau:

1.  **Consolidated Testing:** Thay vì chia nhỏ quá nhiều file, mình gộp các test liên quan vào 3 file chính (`auth`, `tickets`, `bookings`). Điều này giúp dễ dàng quản lý state của database và fixtures.
2.  **Mocking Intelligence:** 
    - Mocking `LangGraph` để kiểm tra logic routing mà không cần tốn chi phí API OpenAI.
    - Mocking `FAISS` và `Embeddings` để test hệ thống cache mà không cần download model thật.
    - Mocking `Async methods` của `AIAdapter` để giả lập các tình huống lỗi graph hoặc pending confirmation.
3.  **Boundary Testing:** Kiểm tra kỹ các trường hợp biên như:
    - Token hết hạn hoặc không hợp lệ.
    - Truy cập tài nguyên không thuộc quyền sở hữu (403 Forbidden).
    - Cập nhật trạng thái không hợp lệ (ví dụ: chuyển từ Resolved sang Pending).
4.  **HITL Automation:** Viết test giả lập phản hồi của người dùng đối với các `interrupt` trong LangGraph, đảm bảo luồng confirm/cancel hoạt động chính xác 100%.

Việc duy trì độ phủ cao giúp hệ thống ổn định khi refactor code AI hoặc thay đổi database schema trong tương lai.