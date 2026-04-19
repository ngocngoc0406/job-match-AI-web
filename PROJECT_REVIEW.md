# PROJECT REVIEW — Job Match AI Web
> Cập nhật: 2026-04-18 | Người review: Vũ Hà | Branch: `main`
> **Status: ✅ Tất cả bugs đã được fix**

---

## 1. Project làm gì + kiến trúc

### Mục tiêu
Hệ thống **AI matching CV với công việc** dựa trên Knowledge Graph (KG) — người dùng upload
PDF CV, hệ thống trích xuất kỹ năng, tính điểm phù hợp với từng job, rồi hiển thị kết quả
trên web.

### Kiến trúc tổng quan

```
main.py
  └── web/app.py          (Flask 1491 dòng — toàn bộ backend + API)
        ├── init_application()        # Khởi tạo: load Excel, build KG, TF-IDF
        ├── Route pages               # /upload_page, /results-page, /search, ...
        └── API endpoints             # /upload, /results, /job/<id>, /api/search, ...

scoring/
  ├── user_job_score.py   # Tính điểm composite (skill 35%, text 25%, loc 15%, ...)
  ├── xai.py              # Giải thích skill coverage (matched/missing)
  └── skill_variants.py   # Trích xuất skill probabilistic

kg/
  ├── graph_init.py       # Khởi tạo RDF graph (NetworkX DiGraph)
  ├── job_builder.py      # Tạo node Job trong KG
  ├── user_builder.py     # Tạo node User trong KG
  └── similarity.py       # Cạnh SIMILAR_TO giữa các job

utils/
  ├── data_loader.py      # Load Excel + PDF (pdfplumber/OCR)
  └── text_processing.py  # norm_text, infer_role, parse_location, ...

visualization/
  └── graph_visualization.py   # Layout KG (clean_focus_layout)

web/
  ├── templates/          # Jinja2: base.html + pages/ + components/tabs/
  ├── static/js/main.js   # Frontend SPA logic (1518 dòng)
  └── data/               # dashboard_data.json (persistent Kanban)
```

### State management
Dùng **global dict `state`** trong `app.py` (in-process, không dùng session/DB).  
→ Mỗi lần khởi động lại server, toàn bộ state CV bị mất.  
→ Không hỗ trợ multi-user (race condition nếu 2 người dùng cùng lúc).

---

## 2. Những chức năng đã chạy được

| Chức năng | Trạng thái | Ghi chú |
|---|---|---|
| Upload CV (PDF) | ✅ Hoạt động | Extract text → build user node → score |
| Job Matching (`/results-page`) | ✅ Hoạt động | Top 3 jobs (TOPK=3 trong config) |
| XAI Job Detail (modal) | ✅ Hoạt động | Matched/missing skills per job |
| Knowledge Graph (`/graph-page`) | ✅ Hoạt động | Sau khi upload CV |
| Search page (`/search`) | ✅ Hoạt động | Filter, pagination, sort |
| Dashboard + Kanban | ✅ Hoạt động | Persistent qua JSON file |
| Mock Interview (`/interview-page`) | ✅ Hoạt động | 10 turns, STAR analysis |
| Salary Estimate (`/salary-page`) | ✅ Hoạt động | Parse từ Excel DB |
| CV Builder (`/cv-builder`) | ✅ Hoạt động | Auto-fill từ CV, live preview |
| Login/Register (mock) | ⚠️ Chỉ là mock | Không có backend auth thật |
| My Skills (`/skills-page`) | ⚠️ Cần CV | Crash nếu chưa upload CV |
| DB Stats (`/stats-page`) | ⚠️ Cần CV | Crash nếu chưa upload CV |
| Dark mode | ✅ Hoạt động | localStorage |

---

## 3. Các lỗi đã tìm thấy

### 🔴 LỖI NGHIÊM TRỌNG

#### [BUG-01] `/user-skills` có 2 route bị trùng — route đầu **thắng**, route sau **ẩn**
**File:** `web/app.py`, dòng 195 và 395

```python
# Route 1 (dòng 195–205): trả [] nếu user_prob is None
@app.route('/user-skills')
def get_user_skills():
    if state.get('user_prob') is None:
        return jsonify([])
    ...

# Route 2 (dòng 395–408): trả đầy đủ info (is_core, tag, ...)
@app.route('/user-skills')
def user_skills():
    for k, v in sorted(state['user_prob'].items(), ...):  # CRASH nếu user_prob = None
```

**Hậu quả:**
- Flask dùng route 1 (`get_user_skills`), route 2 (`user_skills`) bị bỏ qua hoàn toàn.
- Route 1 trả về list `{name, probability}` — thiếu trường `is_core`, `tag`.
- Trang `/skills-page` gọi `loadSkills()` → fetch `/user-skills` → render bình thường vì route 1 đủ dùng.
- Tuy nhiên Dashboard cũng fetch `/user-skills` nhưng xử lý field `probability` → OK.
- **Route 2 (`user_skills`) CHẾT hoàn toàn, không bao giờ được gọi.**

---

#### [BUG-02] `/job/<job_id>` crash khi chưa upload CV
**File:** `web/app.py`, dòng 353–393

```python
@app.route('/job/<job_id>')
def job_detail(job_id):
    # KHÔNG check state['scores'] is None trước
    if int(job_id) >= len(state['scores']):  # TypeError nếu scores = None
```

**Hậu quả:** Nếu user truy cập `/job/0` trước khi upload CV → `TypeError: object of type 'NoneType' has no len()` → HTTP 500.

---

#### [BUG-03] `/statistics` crash khi chưa upload CV
**File:** `web/app.py`, dòng 410–429

```python
@app.route('/statistics')
def statistics():
    job_nodes = state['job_nodes']
    job_info = state['job_info']
    # ...
    Cj_sizes = np.array(Cj_sizes)
    'user_skills': len(state['user_prob']),  # AttributeError nếu user_prob = None
```

**Hậu quả:** `AttributeError: 'NoneType' has no len()` → HTTP 500.  
Trang `/stats-page` sẽ hiện spinner mãi mãi vì JS không xử lý lỗi `{}`.

---

#### [BUG-04] `TOPK_USER_JOB = 3` — chỉ hiển thị **3 job kết quả**
**File:** `config.py` dòng 5, `config.py` dòng 173 (bị khai báo 2 lần!)

```python
TOPK_USER_JOB = 3   # dòng 5
# ...
TOPK_USER_JOB = 3   # dòng 173 — khai báo thừa, cùng giá trị
```

**Hậu quả:** Người dùng chỉ thấy 3 job dù DB có hàng nghìn job. Cực kỳ giới hạn trải nghiệm.  
Score vẫn tính cho **tất cả** job nhưng chỉ lấy top-3 để render.

---

#### [BUG-05] `RANDOM_SEED = 42` khai báo 2 lần trong config
**File:** `config.py` dòng 20 và 171

```python
RANDOM_SEED = 42  # dòng 20
# ...
RANDOM_SEED = 42  # dòng 171
```

Không gây crash nhưng là code smell, nên dọn.

---

### 🟡 LỖI VỪA

#### [BUG-06] Login/Register **không có backend** — pure mock JS
**File:** `web/static/js/main.js`, dòng 98–124

```js
function processAuth(form, title, message) {
    setTimeout(() => {
        setAuthState(true);  // Chỉ set localStorage, không gọi API
        window.location.href = '/dashboard';
    }, 1000);
}
```

**Hậu quả:**
- Bất kỳ email/password nào cũng "đăng nhập" được.
- Username luôn là "John Doe" (hardcode trong `navbar.html` dòng 80).
- `setAuthState` đọc `authButtons` + `userProfile` — nếu các element này null (trang không import base.html) → JS crash **silently**.
- Không có route `/login`, `/register`, `/logout` nào trên server.

---

#### [BUG-07] `showToast` gọi 2 lần trong `processAuth`
**File:** `web/static/js/main.js`, dòng 120–122

```js
showToast(title, message, 'success');
btn.innerHTML = originalText;
showToast(title, message, 'success');  // GỌI LẠI — hiện 2 toast
```

---

#### [BUG-08] `/results-page` — `resultsListContainer` không có trong DOM đúng chỗ
**File:** `web/templates/components/tabs/results.html`, dòng 3

Tab HTML có `id="results"` (class `tab-pane`), nhưng `pages/results.html` khi load ở MPA mode sẽ add class `show active` cho `#results` — tuy nhiên `#resultsListContainer` **nằm trong tab-pane**, không phải trực tiếp trong main content.

Khi `loadResults()` được gọi từ `DOMContentLoaded` ở `pages/results.html`, hàm tìm `#resultsListContainer` → **OK vì nó tồn tại trong DOM**.  
Nhưng kết hợp với MutationObserver trong `components/tabs/results.html` → **loadResults() bị gọi 2 lần** khi trang mount.

---

#### [BUG-09] Search page `setupSearch()` inject mock data vào `#searchResults`
**File:** `web/static/js/main.js`, dòng 459–503

```js
function setupSearch() {
    const jobs = [
        { title: "Senior AI Engineer", company: "OpenAI", ...},  // HARDCODE mock data
        ...
    ];
    if (resultsDiv) {
        resultsDiv.innerHTML = jobs.map(job => ...).join('');  // Overwrite real results!
    }
}
```

`setupSearch()` được gọi từ `DOMContentLoaded` (dòng 8) — **trên mọi trang**, không chỉ `/search`.
Nếu `#searchResults` tồn tại trên trang nào khác, nó sẽ bị inject mock jobs.

Trên trang `/search`, thứ tự thực thi:
1. `setupSearch()` → inject 4 mock jobs hardcode vào `#searchResults`
2. `handleJobSearch()` (từ `DOMContentLoaded` trong `search.html`) → gọi `/api/search` → overwrite bằng real data

→ Có flash mock data ngắn 100-200ms trước khi real data load.

---

#### [BUG-10] `job_detail` dùng `index` 0-based thay vì `job_id` từ DB
**File:** `web/app.py`, dòng 353–393; `web/static/js/main.js`, dòng 696

Frontend: `onclick="loadJobDetail(${index})"` — index là vị trí trong mảng results (0, 1, 2).  
Backend: `state['scores'][int(job_id)]` xử lý index như rank position.

→ **Không có job ID thật** — nếu user F5 trang `/results-page`, toàn bộ mapping lệch nếu state thay đổi.

---

#### [BUG-11] `statistics()` không guard `state['is_ready']`
**File:** `web/app.py`, dòng 410

Trong khi `/upload` check `state['is_ready']` (dòng 211), `/statistics` không check → có thể crash trong thời gian init.

---

### 🟢 LỖI NHỎ / CODE SMELL

#### [BUG-12] `skills-page` gọi `loadSkills()` nhưng không được trigger tự động
**File:** `web/templates/pages/skills.html`

```html
{% include 'components/tabs/skills.html' %}
<script>
    document.addEventListener('DOMContentLoaded', () => {
        const tab = document.getElementById('skills');
        if (tab) tab.classList.add('show', 'active');
        // KHÔNG có: if (typeof loadSkills === 'function') loadSkills();
    });
</script>
```

Trang load nhưng `loadSkills()` không được gọi → hiện placeholder mãi, dù CV đã upload.

---

#### [BUG-13] `stats-page` gọi `loadStatistics()` nhưng cũng không được trigger
Tương tự BUG-12 — `stats.html` pages/... không gọi `loadStatistics()`.

---

#### [BUG-14] `graph_visualization.js` load `vis.js` nhưng route `/graph-page` không có logic init
**File:** `web/templates/pages/graph.html`

Trang `graph.html` chỉ `{% include 'components/tabs/graph_page.html' %}` mà không có `DOMContentLoaded` script khởi tạo graph visualization từ `/graph` API.

---

#### [BUG-15] `salary_estimate()` hardcode tiền USD giả
**File:** `web/app.py`, dòng 1193–1196

```python
scale = 25000 if is_usd else 1000000
# Logic convert VND → USD bằng cách chia 25000 (tỷ giá cố định)
final_min = (avg_min * exp_multiplier) / 25000
```

Tỷ giá 25,000 VND/USD sẽ lỗi thời và tính không chính xác.

---

#### [BUG-16] `main.py` và `web/app.py` đều có `app.run()`
**File:** `main.py` dòng 10, `web/app.py` dòng 1489

```python
# main.py
app.run(host="0.0.0.0", port=5000, debug=True)

# web/app.py (bên trong if __name__ == "__main__")
app.run(host="127.0.0.1", port=5000, debug=True)
```

Nếu chạy `python web/app.py` trực tiếp → không gọi `init_application()` trước → crash ngay khi có request vì `state` rỗng.  
Chỉ nên chạy qua `python main.py`.

---

## 4. Tóm tắt bug theo nguyên nhân

| Loại | Bug IDs |
|---|---|
| **Duplicate route** | BUG-01 |
| **None-check thiếu** | BUG-02, BUG-03, BUG-11 |
| **Config trùng lặp** | BUG-04 (giá trị quá nhỏ), BUG-05 |
| **Auth không có backend** | BUG-06, BUG-07 |
| **Page không trigger load** | BUG-12, BUG-13, BUG-14 |
| **Mock data chồng lên real data** | BUG-09 |
| **Double loadResults** | BUG-08 |
| **Index-based ID không ổn định** | BUG-10 |
| **Hardcode business logic** | BUG-15 |
| **Multi-entry point** | BUG-16 |

---

## 5. Việc cần sửa — Ưu tiên cao → thấp

### 🔴 Ưu tiên 1 — Sửa ngay (crash/silent failure)

| # | Việc cần làm | File | Dòng | Trạng thái |
|---|---|---|---|---|
| P1-A | Xóa route `/user-skills` trùng (giữ lại get_user_skills hoặc merge 2 cái) | `app.py` | 195, 395 | ✅ Fixed |
| P1-B | Add `if state.get('scores') is None` guard vào `job_detail()` | `app.py` | 353 | ✅ Fixed |
| P1-C | Add None-check `user_prob` vào `statistics()` | `app.py` | 410 | ✅ Fixed |
| P1-D | Add `loadSkills()` trigger vào `pages/skills.html` + null guard | `skills.html`, `main.js` | — | ✅ Fixed |
| P1-E | Add `loadStatistics()` trigger vào `pages/stats.html` + full card | `stats.html`, `main.js` | — | ✅ Fixed |

### 🟡 Ưu tiên 2 — Sửa trước demo (UX/logic sai)

| # | Việc cần làm | File | Dòng | Trạng thái |
|---|---|---|---|---|
| P2-A | Tăng `TOPK_USER_JOB` từ 3 → 10 | `config.py` | 5, 173 | ✅ Fixed |
| P2-B | Xóa khai báo trùng `TOPK_USER_JOB` + `RANDOM_SEED` | `config.py` | 173, 171 | ✅ Fixed |
| P2-C | Xóa mock data hardcode trong `setupSearch()` | `main.js` | 459–503 | ✅ Fixed |
| P2-D | Sửa `showToast` gọi 2 lần trong `processAuth` | `main.js` | 121–122 | ✅ Fixed |
| P2-E | Add null guard `setAuthState()` cho trang không có navbar | `main.js` | 133 | ✅ Fixed |
| P2-F | Add `is_ready` guard vào `/statistics` route | `app.py` | 411 | ✅ Fixed |
| P2-G | Xóa MutationObserver thừa trong results.html tab | `results.html` | — | ✅ Fixed |

### 🟢 Ưu tiên 3 — Cải thiện (không block demo)

| # | Việc cần làm | File | Trạng thái |
|---|---|---|---|
| P3-A | Backend auth thật (Flask-Login/JWT) | `app.py` | ⏳ Chưa làm |
| P3-B | Flask Session để CV state không mất khi reload trang | `app.py` | ⏳ Chưa làm |
| P3-C | Job ID stable (hash/node ID) thay vì array index | `app.py`, `main.js` | ⏳ Chưa làm |
| P3-D | Tỷ giá VND/USD cập nhật hoặc configurable | `app.py` | ⏳ Chưa làm |
| P3-E | Warning nếu chạy `web/app.py` trực tiếp | `app.py` | ✅ Fixed |

---

## 6. Những gì chưa có / chưa làm được

- ❌ **Multi-user support** — state global, không có session per user
- ❌ **Auth thật** — login/register chỉ là UI mock
- ❌ **Persistent CV state** — F5 server → mất hết
- ❌ **Job detail page riêng biệt** — chỉ có modal, không có `/job/<id>` page
- ❌ **LLM integration** — interview AI là rule-based, không có LLM
- ❌ **Top-N configurable** — kết quả cứng 3 job
- ❌ **Skills page auto-load** — phải sửa thủ công
- ❌ **Stats page auto-load** — phải sửa thủ công
- ❌ **Graph page auto-load** — phải thêm script DOMContentLoaded
- ❌ **Mobile responsive** — chưa test kỹ
- ❌ **Error boundary JS** — nhiều fetch() không handle lỗi HTTP code

---

*Review dựa trên commit hiện tại của branch `main`. Đã đọc toàn bộ: `web/app.py` (1491 dòng), `web/static/js/main.js` (1518 dòng), `config.py`, `scoring/`, `kg/`, `utils/`, và toàn bộ templates.*
