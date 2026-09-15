# Sumopod AI Service Integration

Service untuk integrasi AI-powered caption generation dan analisis hashtag menggunakan Sumopod API.

## Setup

1. Install dependencies:
```bash
pip install openai python-dotenv
```

2. Konfigurasi API Key di `.env`:
```env
SUMOPOD_API_KEY=sk-your-api-key-here
```

## Methods yang Tersedia

### 1. `generate_caption_from_recommendations()`
Generate caption Instagram berdasarkan rekomendasi hashtag.

**Parameters yang Sesuai dengan UI:**
- ✅ `university_names: List[str]` - Dari **Universitas referensi** (dropdown/multiselect)
- ✅ `content_type: str` - Dari **Tipe konten** (radio: foto/video/semua)
- ✅ `recommended_hashtags: List[str]` - Hashtag hasil rekomendasi dengan filter **minimum lift**
- ✅ `initial_hashtags: List[str]` - Dari **Hashtag yang sudah direncanakan** (opsional)
- `tone: str` - Tone caption (professional, casual, engaging, formal)
- `stream: bool` - Enable streaming response untuk UX yang lebih baik

**Return:** String caption atau Generator (jika stream=True)

### 2. `analyze_recommendations_context()`
Generate analisis kontekstual dari hasil rekomendasi.

**Parameters yang Sesuai dengan UI:**
- ✅ `recommended_rules: List[dict]` - Rules yang sudah difilter berdasarkan **jumlah rekomendasi** (slider 5-20)
- ✅ `university_names: List[str]` - Dari **Universitas referensi**
- ✅ `content_type: str` - Dari **Tipe konten**
- ✅ `min_lift: float` - Dari **Minimum lift** (slider 1.0-3.0)

**Return:** String analisis insights

### 3. `optimize_hashtags()`
Expand dan optimize hashtag list.

**Parameters:**
- `initial_hashtags: List[str]` - Hashtag awal
- `target_audience: str` - Target audience (mahasiswa, alumni, dll)
- `max_hashtags: int` - Maksimal hashtag yang dihasilkan

**Return:** List[str] hashtags

### 4. `generate_content_ideas()`
Generate ide konten berdasarkan hashtag.

**Parameters:**
- `hashtags: List[str]` - Hashtag sebagai basis
- `content_type: str` - Tipe konten (post, story, reel, carousel)
- `num_ideas: int` - Jumlah ide

**Return:** List[str] content ideas

## Mapping UI ke Service

| Input UI | Type | Wajib? | Mapping ke Service |
|----------|------|--------|-------------------|
| Universitas referensi | Dropdown/multiselect | Ya | `university_names` parameter |
| Tipe konten | Radio button | Ya | `content_type` parameter ("foto"/"video"/"semua") |
| Hashtag yang sudah direncanakan | Text input | Opsional | `initial_hashtags` parameter |
| Jumlah rekomendasi | Slider (5-20) | Ya | Filter rules sebelum pass ke service |
| Minimum lift | Slider (1.0-3.0) | Ya | Filter rules dengan `lift >= min_lift` sebelum pass ke service |

## Contoh Penggunaan

```python
from services.sumopod_service import get_sumopod_service

# Initialize service
sumopod = get_sumopod_service()

# 1. Filter rules dari Apriori berdasarkan UI inputs
filtered_rules = [
    rule for rule in all_rules
    if rule['lift'] >= min_lift_from_slider
][:jumlah_rekomendasi_from_slider]

# 2. Extract recommended hashtags
recommended_hashtags = []
for rule in filtered_rules:
    recommended_hashtags.extend(rule.get('consequents', []))
recommended_hashtags = list(set(recommended_hashtags))

# 3. Generate caption dengan streaming
caption_placeholder = st.empty()
full_caption = ""

for chunk in sumopod.generate_caption_from_recommendations(
    recommended_hashtags=recommended_hashtags,
    university_names=selected_universities,  # Dari multiselect
    content_type=selected_content_type,      # Dari radio button
    initial_hashtags=user_input_hashtags,    # Dari text input (opsional)
    stream=True
):
    full_caption += chunk
    caption_placeholder.markdown(full_caption)

# 4. Generate analisis insights
analysis = sumopod.analyze_recommendations_context(
    recommended_rules=filtered_rules,
    university_names=selected_universities,
    content_type=selected_content_type,
    min_lift=min_lift_from_slider
)
st.info(analysis)
```

## Error Handling

Service akan raise exception jika:
- API key tidak ditemukan
- API request gagal
- Response timeout

Gunakan try-except untuk handle errors:
```python
try:
    caption = sumopod.generate_caption_from_recommendations(...)
except Exception as e:
    st.error(f"Error: {str(e)}")
```
