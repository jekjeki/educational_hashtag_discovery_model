"""
services/sumopod_service.py
Service untuk integrasi dengan Sumopod AI API untuk generate rekomendasi caption dan hashtag.
Menggunakan OpenAI-compatible API dengan Grounded Recommendation System.
"""

import os
import json
import re
from typing import List, Optional, Generator, Dict, Tuple
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from config import SUMOPOD_CONFIG

load_dotenv()

# Import viral scoring module (bypass core/__init__.py to avoid mlxtend dependency)
VIRAL_SCORING_AVAILABLE = False
get_vocabulary_for_grounding = None
enrich_recommendations_with_viral_scores = None
batch_calculate_viral_scores = None

try:
    import importlib.util
    import sys
    from pathlib import Path

    # Get the path to viral_scoring.py
    current_dir = Path(__file__).parent.parent
    viral_scoring_path = current_dir / "core" / "viral_scoring.py"

    if viral_scoring_path.exists():
        spec = importlib.util.spec_from_file_location("viral_scoring", viral_scoring_path)
        viral_scoring_module = importlib.util.module_from_spec(spec)
        sys.modules["viral_scoring"] = viral_scoring_module
        spec.loader.exec_module(viral_scoring_module)

        get_vocabulary_for_grounding = viral_scoring_module.get_vocabulary_for_grounding
        enrich_recommendations_with_viral_scores = viral_scoring_module.enrich_recommendations_with_viral_scores
        batch_calculate_viral_scores = viral_scoring_module.batch_calculate_viral_scores
        VIRAL_SCORING_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not load viral_scoring module: {e}")
    VIRAL_SCORING_AVAILABLE = False

class SumopodService:

    def __init__(self):
        """Initialize Sumopod service dengan API key dari environment atau secrets."""
        self.api_key = self._get_api_key()
        self.base_url = SUMOPOD_CONFIG["base_url"]
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.model = SUMOPOD_CONFIG["model"]

    def _get_api_key(self) -> str:
        try:
            if hasattr(st, 'secrets') and 'SUMOPOD_API_KEY' in st.secrets:
                return st.secrets['SUMOPOD_API_KEY']
        except Exception:
            pass

        # Fallback to environment variable
        api_key = os.getenv('SUMOPOD_API_KEY', '')

        if not api_key:
            raise ValueError(
                "SUMOPOD_API_KEY tidak ditemukan. "
                "Tambahkan ke .streamlit/secrets.toml atau environment variable."
            )

        return api_key

    def is_configured(self) -> bool:
        """Check apakah API key sudah dikonfigurasi."""
        try:
            self._get_api_key()
            return True
        except ValueError:
            return False

    def generate_caption_from_recommendations(
        self,
        recommended_hashtags: List[str],
        university_names: List[str],
        content_type: str = "semua",
        initial_hashtags: Optional[List[str]] = None,
        tone: str = "professional",
        max_tokens: int = 400,
        stream: bool = False
    ):
        """
        Generate caption untuk Instagram berdasarkan rekomendasi hashtag.

        Args:
            recommended_hashtags: List hashtag hasil rekomendasi
            university_names: List nama universitas referensi
            content_type: Tipe konten (foto, video, semua)
            initial_hashtags: Hashtag yang sudah direncanakan user (opsional)
            tone: Tone caption (professional, casual, engaging, formal)
            max_tokens: Maksimal token untuk response
            stream: Apakah menggunakan streaming response

        Returns:
            String caption (jika stream=False) atau Generator (jika stream=True)
        """
        # Build prompt
        hashtags_str = ", ".join([f"#{tag.lstrip('#')}" for tag in recommended_hashtags])
        univ_str = ", ".join(university_names)

        # Content type context
        content_context = {
            "foto": "konten foto/carousel yang visual dan menarik",
            "video": "konten video/reel yang dinamis dan engaging",
            "semua": "konten Instagram yang versatile (bisa foto maupun video)"
        }.get(content_type, "konten Instagram")

        prompt = f"""Kamu adalah seorang social media specialist untuk universitas di Indonesia.

Konteks:
- Universitas referensi: {univ_str}
- Tipe konten: {content_context}
- Hashtag yang direkomendasikan: {hashtags_str}
"""

        if initial_hashtags:
            initial_str = ", ".join([f"#{tag.lstrip('#')}" for tag in initial_hashtags])
            prompt += f"- Hashtag yang sudah direncanakan: {initial_str}\n"

        prompt += f"""- Tone: {tone}
- Bahasa: Indonesia

Buatkan caption Instagram yang:
1. Engaging dan menarik perhatian mahasiswa/calon mahasiswa
2. Sesuai dengan tipe konten {content_type}
3. Mencerminkan nilai-nilai akademik dan semangat kampus
4. Menggunakan emoji yang relevan (maksimal 3-4)
5. Panjang ideal untuk Instagram (120-180 kata)
6. Natural dan tidak terlalu promotional
7. Sertakan call-to-action yang subtle
8. Gunakan hashtag di akhir caption

Format output: Langsung tulis caption-nya saja tanpa penjelasan tambahan atau label.
"""

        messages = [{"role": "user", "content": prompt}]

        try:
            if stream:
                # Return generator untuk streaming
                return self._stream_response(messages, max_tokens)
            else:
                # Return complete response
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                    stream=False
                )
                return response.choices[0].message.content.strip()

        except Exception as e:
            raise Exception(f"Error generating caption: {str(e)}")

    def _stream_response(self, messages: List[dict], max_tokens: int) -> Generator:
        """Internal method untuk streaming response."""
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    def optimize_hashtags(
        self,
        initial_hashtags: List[str],
        target_audience: Optional[str] = None,
        max_hashtags: int = 15
    ) -> List[str]:
        """
        Optimize dan expand hashtag list berdasarkan trending dan relevance.

        Args:
            initial_hashtags: Hashtag awal yang sudah ada
            target_audience: Target audience (mahasiswa, alumni, calon mahasiswa, dll)
            max_hashtags: Maksimal jumlah hashtag yang dihasilkan

        Returns:
            List of optimized hashtags
        """
        hashtags_str = ", ".join([f"#{tag.lstrip('#')}" for tag in initial_hashtags])

        prompt = f"""Kamu adalah social media expert untuk universitas di Indonesia.

Berdasarkan hashtag awal: {hashtags_str}
Target audience: {target_audience or 'mahasiswa dan calon mahasiswa'}

Buatkan daftar {max_hashtags} hashtag yang:
1. Relevan dengan konteks pendidikan tinggi
2. Mix antara hashtag populer dan niche
3. Sesuai untuk Instagram
4. Dalam Bahasa Indonesia dan Inggris
5. Mempertimbangkan trending topic kampus

Format output: Tulis satu hashtag per baris, dimulai dengan #, tanpa penjelasan.
Contoh:
#kampus
#mahasiswa
#universitasindonesia
"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.8,
                stream=False
            )

            # Parse response menjadi list hashtags
            content = response.choices[0].message.content.strip()
            hashtags = [
                line.strip()
                for line in content.split('\n')
                if line.strip().startswith('#')
            ]

            return hashtags[:max_hashtags]

        except Exception as e:
            raise Exception(f"Error optimizing hashtags: {str(e)}")

    def analyze_recommendations_context(
        self,
        recommended_rules: List[dict],
        university_names: List[str],
        content_type: str = "semua",
        min_lift: float = 1.0
    ) -> str:
        """
        Generate analisis kontekstual dari rekomendasi hashtag.

        Args:
            recommended_rules: List rules yang direkomendasikan
            university_names: Nama universitas referensi
            content_type: Tipe konten (foto/video/semua)
            min_lift: Minimum lift value

        Returns:
            String analisis dan insights
        """
        if not recommended_rules:
            return "Tidak ada rekomendasi yang sesuai dengan kriteria."

        # Extract hashtags dan statistik
        all_hashtags = set()
        avg_lift = 0
        max_lift = 0

        for rule in recommended_rules:
            all_hashtags.update(rule.get("consequents", []))
            lift = rule.get("lift", 0)
            avg_lift += lift
            max_lift = max(max_lift, lift)

        avg_lift = avg_lift / len(recommended_rules) if recommended_rules else 0

        hashtags_str = ", ".join([f"#{tag}" for tag in sorted(all_hashtags)[:10]])
        univ_str = ", ".join(university_names)

        prompt = f"""Kamu adalah data analyst untuk social media universitas.

Berdasarkan analisis data:
- Universitas referensi: {univ_str}
- Tipe konten: {content_type}
- Total rekomendasi: {len(recommended_rules)} kombinasi hashtag
- Average lift: {avg_lift:.2f}
- Maximum lift: {max_lift:.2f}
- Minimum lift threshold: {min_lift}
- Top hashtag yang direkomendasikan: {hashtags_str}

Buatkan analisis singkat (3-4 kalimat) yang menjelaskan:
1. Mengapa hashtag-hashtag ini direkomendasikan
2. Pola apa yang ditemukan dari data universitas referensi
3. Bagaimana hashtag ini bisa meningkatkan engagement

Tulis dalam bahasa Indonesia yang profesional tapi tetap mudah dipahami.
Format output: Langsung tulis analisisnya tanpa label atau heading.
"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=300,
                temperature=0.6,
                stream=False
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Error generating analysis: {str(e)}"

    def generate_content_ideas(
        self,
        hashtags: List[str],
        content_type: str = "post",
        num_ideas: int = 5
    ) -> List[str]:
        """
        Generate ide konten berdasarkan hashtag.

        Args:
            hashtags: List hashtag sebagai basis
            content_type: Tipe konten (post, story, reel, carousel)
            num_ideas: Jumlah ide yang diinginkan

        Returns:
            List of content ideas
        """
        hashtags_str = ", ".join([f"#{tag.lstrip('#')}" for tag in hashtags])

        prompt = f"""Kamu adalah content strategist untuk social media universitas.

Berdasarkan hashtag: {hashtags_str}
Tipe konten: {content_type}

Buatkan {num_ideas} ide konten Instagram yang:
1. Menarik dan engaging untuk mahasiswa
2. Sesuai dengan format {content_type}
3. Mudah diproduksi
4. Memiliki potensi viral
5. Tetap profesional dan edukatif

Format output: Tulis setiap ide dalam 1-2 kalimat, nomor 1-{num_ideas}.
"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=600,
                temperature=0.9,
                stream=False
            )

            content = response.choices[0].message.content.strip()
            # Parse menjadi list
            ideas = [
                line.strip()
                for line in content.split('\n')
                if line.strip() and any(line.strip().startswith(f"{i}.") for i in range(1, num_ideas + 2))
            ]

            return ideas[:num_ideas]

        except Exception as e:
            raise Exception(f"Error generating content ideas: {str(e)}")

    def enrich_hashtag_recommendations(
        self,
        arm_candidates: List[str],
        content_description: str,
        university_names: List[str],
        content_type: str = "semua",
        user_hashtags: Optional[List[str]] = None,
        max_recommendations: int = 15
    ) -> dict:
        """
        Enrich hashtag recommendations dengan GPT untuk evaluasi relevansi dan
        augmentasi semantik. Menghasilkan output JSON terstruktur.

        Args:
            arm_candidates: List hashtag hasil ARM mining (dari semua universitas)
            content_description: Deskripsi/konten dari user
            university_names: List nama universitas referensi
            content_type: Tipe konten (foto, video, semua)
            user_hashtags: Hashtag yang sudah direncanakan user (opsional)
            max_recommendations: Maksimal jumlah hashtag final

        Returns:
            dict dengan struktur:
            {
                "recommendations": [
                    {
                        "hashtag": "nama_hashtag",
                        "source": "arm" | "gpt" | "both",
                        "confidence": 0.85,
                        "lift": 2.5,
                        "reasoning": "Alasan mengapa hashtag ini direkomendasikan"
                    },
                    ...
                ],
                "summary": "Ringkasan rekomendasi",
                "_raw_response": "Debug: raw GPT response"
            }
        """
        import json
        import re

        # Prepare inputs
        arm_set_lower = set(t.lower() for t in arm_candidates)
        candidates_str = ", ".join([f"#{t.lstrip('#')}" for t in arm_candidates]) if arm_candidates else "(tidak ada)"
        univ_str = ", ".join(university_names)
        user_tags_str = ", ".join([f"#{t.lstrip('#')}" for t in user_hashtags]) if user_hashtags else "(tidak ada)"

        # — Simple, direct prompt — no markdown, minimal formatting
        prompt = f"""Deskripsi konten: {content_description}

Universitas: {univ_str}
Tipe konten: {content_type}

Hashtag dari data ARM: {candidates_str}
Hashtag user: {user_tags_str}

Buat rekomendasi {max_recommendations} hashtag Instagram dalam format JSON SAJA.
{{
  "recommendations": [
    {{"hashtag": "nama", "source": "arm/gpt/both", "confidence": null, "lift": null, "reasoning": "alasan"}}
  ],
  "summary": "kesimpulan"
}}

Aturan:
- source="arm" jika hashtag berasal dari data ARM dan relevan
- source="gpt" jika hashtag baru dari GPT karena relevan secara semantik
- source="both" jika hashtag ARM tetap dipertahankan dan juga masuk akal
- "confidence" dan "lift": isi angka jika source="arm" atau "both", null jika source="gpt"
- Prioritaskan hashtag ARM yang relevan
- PENTING: JANGAN gunakan hashtag yang mengandung nama universitas (Binus, Telkom, Atmajaya, UAJY, UII, UMY, PCU, Petra, UMS, dll)
- JANGAN gunakan hashtag seperti WisudaBinus, WisudaUII, KampusTelkom, dll yang menggabungkan kata dengan nama kampus
- Fokus pada hashtag GENERIK yang bisa digunakan oleh SEMUA universitas
- Maksimal {max_recommendations} hashtag
- TANPA MARKDOWN, TANPA PENJELASAN, HANYA JSON"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=3000,
                temperature=0.3
            )

            raw_content = response.choices[0].message.content or ""
            content = raw_content.strip()

            # Debug: save raw response
            debug_raw = content if len(content) < 500 else content[:500] + "..."

            # — Parsing strategies —
            result = None

            # Strategy 1: Direct JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                pass

            # Strategy 2: Markdown code block
            if result is None:
                m = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
                if m:
                    try:
                        result = json.loads(m.group(1).strip())
                    except json.JSONDecodeError:
                        pass

            # Strategy 3: Braces
            if result is None:
                m = re.search(r'\{[\s\S]*\}', content)
                if m:
                    try:
                        result = json.loads(m.group())
                    except json.JSONDecodeError:
                        pass

            # Strategy 4: Fallback — extract all words as hashtags
            if result is None:
                # Find all word-like tokens (hashtag or not)
                all_words = re.findall(r'[#]?(\w{3,})', content)
                seen = set()
                recommendations = []
                for word in all_words:
                    w = word.lower()
                    if w not in seen and w not in ('json', 'recommendations', 'summary', 'hashtag', 'source', 'reasoning', 'confidence', 'null', 'dan', 'yang', 'dengan', 'untuk', 'dari'):
                        seen.add(w)
                        in_arm = w in arm_set_lower
                        recommendations.append({
                            "hashtag": w,
                            "source": "arm" if in_arm else "gpt",
                            "confidence": None,
                            "lift": None,
                            "reasoning": "Direkomendasikan berdasarkan analisis konten."
                        })
                        if len(recommendations) >= max_recommendations:
                            break
                result = {
                    "recommendations": recommendations,
                    "summary": f"Direkomendasikan {len(recommendations)} hashtag."
                }

            # Validate
            recs = result.get("recommendations", [])
            if not isinstance(recs, list) or len(recs) == 0:
                recs = []

            # Filter keywords nama universitas
            univ_keywords = {
                "binus", "telkom", "atmajaya", "uajy", "uii", "umy",
                "pcu", "petra", "ums", "universitas", "univ",
                "binusuniversity", "telkomuniversity", "petrauniversity",
                "atmajayayogyakarta", "uiiofficial", "umygm", "umsofficial",
            }

            for r in recs:
                if not isinstance(r, dict):
                    continue
                if "hashtag" not in r or not r["hashtag"]:
                    continue
                r.setdefault("source", "gpt")
                r.setdefault("confidence", None)
                r.setdefault("lift", None)
                r.setdefault("reasoning", "")

            # Filter out hashtags yang mengandung nama universitas
            result["recommendations"] = [
                r for r in recs
                if isinstance(r, dict) and r.get("hashtag")
                and r.get("hashtag", "").lower() not in univ_keywords
                and not any(keyword in r.get("hashtag", "").lower() for keyword in univ_keywords)
            ]
            result.setdefault("summary", "")
            result["_raw_response"] = debug_raw

            return result

        except Exception as e:
            return {
                "recommendations": [],
                "summary": f"Error: {str(e)}",
                "_raw_response": str(e)
            }

    def enrich_hashtags_streaming(
        self,
        arm_candidates: List[str],
        content_description: str,
        university_names: List[str],
        content_type: str = "semua",
        user_hashtags: Optional[List[str]] = None,
        max_recommendations: int = 15
    ) -> Generator[str, None, None]:
        """
        Streaming version of enrich_hashtag_recommendations.
        Yields JSON chunks as they arrive.
        """
        import json

        candidates_str = ", ".join([f"#{tag.lstrip('#')}" for tag in arm_candidates])
        univ_str = ", ".join(university_names)
        user_tags_str = ", ".join([f"#{tag.lstrip('#')}" for tag in user_hashtags]) if user_hashtags else ""

        content_context = {
            "foto": "konten foto/carousel yang visual",
            "video": "konten video/reel yang dinamis",
            "semua": "konten Instagram"
        }.get(content_type, "konten Instagram")

        system_prompt = """Kamu adalah AI assistant ahli hashtag untuk media sosial institusi pendidikan Indonesia.
Evaluasi hashtag ARM, berikan reasoning, dan augmentasi semantik.

FORMAT OUTPUT: JSON saja.
{
    "recommendations": [
        {"hashtag": "nama", "source": "arm|gpt|both", "confidence": null|0.0-1.0, "lift": null|1.0+, "reasoning": "alasan"}
    ],
    "summary": "ringkasan"
}"""

        prompt = f"""Konten: {content_description}
Universitas: {univ_str}
Tipe: {content_type}
Candidates ARM: {candidates_str}
User hashtags: {user_tags_str or 'tidak ada'}

Evaluasi dan rekomendasikan maksimal {max_recommendations} hashtag. Prioritaskan ARM jika relevan."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=2800,
            temperature=0.3,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    def grounded_hashtag_recommendation(
        self,
        content_description: str,
        university_keys: List[str],
        content_type: str = "semua",
        user_hashtags: Optional[List[str]] = None,
        arm_candidates: Optional[List[str]] = None,
        max_recommendations: int = 15,
        vocabulary_size: int = 100
    ) -> Dict:
        """
        Grounded Recommendation System - GPT hanya boleh memilih dari vocabulary yang diizinkan.
        Menghasilkan rekomendasi dengan viral potential score.

        Args:
            content_description: Deskripsi konten dari user
            university_keys: List key universitas referensi
            content_type: Tipe konten (foto, video, semua)
            user_hashtags: Hashtag yang sudah direncanakan user
            arm_candidates: Hashtag dari ARM mining (opsional, akan digabung dengan vocabulary)
            max_recommendations: Maksimal hashtag yang direkomendasikan
            vocabulary_size: Ukuran vocabulary untuk grounding

        Returns:
            Dict {
                "recommendations": [
                    {
                        "hashtag": str,
                        "source": "arm" | "gpt" | "vocabulary",
                        "viral_score": float,
                        "avg_likes": float,
                        "lift": float,
                        "reasoning": str
                    }
                ],
                "summary": str,
                "confidence": "high" | "medium" | "low",
                "_vocabulary_size": int,
                "_arm_candidates_count": int
            }
        """
        # Get vocabulary dari data historis
        vocabulary = []
        score_map = {}

        if VIRAL_SCORING_AVAILABLE and get_vocabulary_for_grounding:
            try:
                vocabulary, score_map = get_vocabulary_for_grounding(
                    university_keys=university_keys,
                    top_n=vocabulary_size,
                    min_post_count=2
                )
            except Exception as e:
                print(f"Warning: Failed to load vocabulary: {e}")
                vocabulary = []
                score_map = {}

        # Filter university keywords (expanded list) - define early
        univ_keywords = {
            # BINUS
            "binus", "binusian", "binusuniversity", "binussemarang", "binusmalang",
            "binusbandung", "binusbekasi", "binuslife",
            # Telkom
            "telkom", "telu", "telkomuniversity", "telkomedu", "telunews",
            "telucampuslife", "telukampus", "telulife", "iamtelu",
            # Atma Jaya
            "atmajaya", "uajy", "atma", "atmajayayogyakarta", "unikaatmajaya", "uaj",
            # UII
            "uii", "uiiyogyakarta", "uiiofficial", "islamicindonesia",
            # UMY
            "umy", "umyogya", "umygm", "muhammadiyahyogyakarta",
            # PCU / Petra
            "pcu", "petra", "lifeatpcu", "petrachristian", "petrauniversity", "ukpetra",
            # UMS
            "ums", "umsofficial", "umsofficialid", "muhammadiyahsurakarta",
            # Generic
            "universitas", "univ", "kampus",
        }

        vocabulary = [
            v for v in vocabulary
            if v.lower() not in univ_keywords
            and not any(kw in v.lower() for kw in univ_keywords)
        ]

        # Gabungkan ARM candidates ke vocabulary. ARM candidates berasal dari
        # pola asosiasi hashtag input pengguna sehingga paling relevan secara
        # topik, jadi diletakkan di DEPAN daftar agar diprioritaskan LLM.
        arm_set = set()
        arm_ordered = []
        if arm_candidates:
            for t in arm_candidates:
                tl = t.lower().strip()
                if not tl or tl in univ_keywords or any(kw in tl for kw in univ_keywords):
                    continue
                if tl not in arm_set:
                    arm_set.add(tl)
                    arm_ordered.append(tl)
            rest_vocab = [v for v in vocabulary if v.lower() not in arm_set]
            vocabulary = arm_ordered + rest_vocab

        # Prepare prompt
        arm_display = ", ".join([f"#{v}" for v in arm_ordered[:40]])
        vocabulary_str = ", ".join([f"#{v}" for v in vocabulary[:120]])

        prompt = f"""Kamu memilih hashtag Instagram untuk konten pendidikan tinggi.

DESKRIPSI KONTEN:
{content_description}

HASHTAG PALING TERKAIT (dari pola asosiasi input pengguna — prioritaskan jika relevan):
{arm_display if arm_display else "(tidak ada)"}

DAFTAR HASHTAG YANG BOLEH DIPILIH (grounded — HANYA dari daftar ini):
{vocabulary_str}

ATURAN:
1. Pilih HANYA dari daftar di atas. Dilarang menambah hashtag lain.
2. UTAMAKAN RELEVANSI dengan deskripsi konten. Pilih hashtag yang benar-benar berkaitan dengan topik/tema konten.
3. WAJIB abaikan hashtag yang sekadar populer tetapi TIDAK nyambung dengan topik (mis. hashtag rutinitas/umum seperti #jumatberkah bila kontennya bukan tentang itu).
4. Jumlah maksimal {max_recommendations}, tetapi LEBIH BAIK sedikit yang benar-benar relevan daripada memaksa penuh dengan yang tidak relevan.
5. Urutkan dari yang paling relevan dengan topik.

OUTPUT JSON (tanpa markdown, JSON saja):
{{"recommendations":[{{"hashtag":"nama","reasoning":"kenapa relevan dgn topik"}}],"summary":"ringkasan singkat"}}"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2800,
                temperature=0.2
            )

            raw_content = response.choices[0].message.content or ""
            content = raw_content.strip()

            # Parse JSON
            result = None

            # Strategy 1 Direct JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                pass

            # Strategy 2 Markdown code block
            if result is None:
                m = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
                if m:
                    try:
                        result = json.loads(m.group(1).strip())
                    except json.JSONDecodeError:
                        pass

            # Strategy 3 Find JSON object
            if result is None:
                m = re.search(r'\{[\s\S]*\}', content)
                if m:
                    try:
                        result = json.loads(m.group())
                    except json.JSONDecodeError:
                        pass

            # Fallback if JSON parsing fails
            if result is None:
                result = {
                    "recommendations": [],
                    "summary": "",
                    "confidence": "low"
                }

            # Validate dan filter recommendations hanya vocabulary (yang sudah include ARM)
            recs = result.get("recommendations", [])
            valid_recs = []
            vocabulary_set = set(v.lower() for v in vocabulary)

            for r in recs:
                if not isinstance(r, dict):
                    continue

                hashtag = r.get("hashtag", "").lower().strip().lstrip("#")
                if not hashtag:
                    continue

                # Skip university keywords
                if hashtag in univ_keywords or any(kw in hashtag for kw in univ_keywords):
                    continue

                # Hanya terima hashtag dari vocabulary (yang sudah include ARM)
                if hashtag not in vocabulary_set:
                    continue

                # Tentukan source
                source = "arm" if hashtag in arm_set else "vocabulary"

                valid_recs.append({
                    "hashtag": hashtag,
                    "source": source,
                    "reasoning": r.get("reasoning", "Relevan dengan konten"),
                })

            # Fallback bila hasil relevan dari data historis kosong: JANGAN paksakan
            # hashtag populer yang tidak relevan. Sebagai gantinya, minta deepseek
            # menyarankan hashtag relevan sendiri berdasarkan konteks (di luar data
            # historis), ditandai source="ai" agar transparan bagi pengguna.
            if not valid_recs:
                ai_recs = self._free_hashtag_suggestions(content_description, max_recommendations)
                valid_recs.extend(ai_recs)
                if ai_recs and not result.get("summary"):
                    result["summary"] = (
                        "Tidak ada hashtag relevan pada data historis untuk konteks ini, "
                        "sehingga sistem menyarankan hashtag relevan dari luar data historis (AI)."
                    )

            # Enrich with viral scores if available
            if VIRAL_SCORING_AVAILABLE and valid_recs and enrich_recommendations_with_viral_scores:
                enriched = enrich_recommendations_with_viral_scores(
                    valid_recs,
                    university_keys=university_keys
                )
                valid_recs = enriched

            # Debug info
            gpt_suggested_count = len(result.get("recommendations", []))
            filtered_out_count = gpt_suggested_count - len([r for r in valid_recs if r.get("source") != "arm"])

            return {
                "recommendations": valid_recs[:max_recommendations],
                "summary": result.get("summary", ""),
                "confidence": result.get("confidence", "medium"),
                "_vocabulary_size": len(vocabulary),
                "_arm_candidates_count": len(arm_set),
                "_gpt_suggested": gpt_suggested_count,
                "_filtered_out": filtered_out_count,
                "_raw_response": content[:500] if len(content) > 500 else content,
            }

        except Exception as e:
            # Fallback jika error: gunakan vocabulary langsung
            fallback_recs = []

            if vocabulary:
                for tag in vocabulary[:max_recommendations]:
                    tag_lower = tag.lower().strip()
                    source = "arm" if tag_lower in arm_set else "vocabulary"
                    fallback_recs.append({
                        "hashtag": tag_lower,
                        "source": source,
                        "reasoning": "Dari data historis (fallback)",
                    })

            # Enrich fallback with viral scores
            if VIRAL_SCORING_AVAILABLE and fallback_recs and enrich_recommendations_with_viral_scores:
                fallback_recs = enrich_recommendations_with_viral_scores(
                    fallback_recs,
                    university_keys=university_keys
                )

            return {
                "recommendations": fallback_recs[:max_recommendations],
                "summary": f"Fallback mode: {str(e)}",
                "confidence": "low",
                "_vocabulary_size": len(vocabulary),
                "_arm_candidates_count": len(arm_set) if arm_set else 0,
                "_error": str(e),
            }

    def _free_hashtag_suggestions(self, content_description: str, max_n: int = 15) -> List[dict]:
        """
        Saran hashtag Instagram relevan berbasis konteks TANPA batasan vocabulary
        data historis. Dipakai sebagai fallback ketika data historis tidak memuat
        hashtag relevan. Hasil ditandai source="ai" (di luar data historis).
        """
        import re as _re
        prompt = f"""Sarankan maksimal {max_n} hashtag Instagram yang RELEVAN untuk konten pendidikan tinggi berikut.

DESKRIPSI KONTEN:
{content_description}

ATURAN:
1. Hashtag harus benar-benar relevan dengan topik/tema konten.
2. Gunakan hashtag umum yang mudah dicari di Instagram (boleh campuran Indonesia/Inggris).
3. Tulis nama hashtag tanpa tanda #.

OUTPUT JSON saja: {{"recommendations":[{{"hashtag":"nama","reasoning":"alasan singkat"}}]}}"""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.4,
            )
            content = (resp.choices[0].message.content or "").strip()
            m = _re.search(r'\{[\s\S]*\}', content)
            data = json.loads(m.group()) if m else {}
            out = []
            for r in data.get("recommendations", [])[:max_n]:
                if not isinstance(r, dict):
                    continue
                tag = str(r.get("hashtag", "")).lower().strip().lstrip("#")
                if tag:
                    out.append({
                        "hashtag": tag,
                        "source": "ai",
                        "reasoning": r.get("reasoning", "Saran AI berbasis konteks"),
                    })
            return out
        except Exception:
            return []

    def get_fallback_recommendations(
        self,
        university_keys: List[str],
        content_description: str = "",
        max_recommendations: int = 15
    ) -> List[Dict]:
        """
        Fallback recommendation tanpa GPT - langsung dari data historis.
        Digunakan jika GPT tidak tersedia atau error.

        Returns:
            List of hashtag recommendations dengan viral scores
        """
        if not VIRAL_SCORING_AVAILABLE:
            return []

        # Get top viral hashtags
        vocabulary, score_map = get_vocabulary_for_grounding(
            university_keys=university_keys,
            top_n=max_recommendations * 2,
            min_post_count=2
        )

        # Filter university keywords (expanded list)
        univ_keywords = {
            # BINUS
            "binus", "binusian", "binusuniversity", "binussemarang", "binusmalang",
            "binusbandung", "binusbekasi", "binuslife",
            # Telkom
            "telkom", "telu", "telkomuniversity", "telkomedu", "telunews",
            "telucampuslife", "telukampus", "telulife", "iamtelu",
            # Atma Jaya
            "atmajaya", "uajy", "atma", "atmajayayogyakarta", "unikaatmajaya",
            # UII
            "uii", "uiiyogyakarta", "uiiofficial", "islamicindonesia",
            # UMY
            "umy", "umyogya", "umygm", "muhammadiyahyogyakarta",
            # PCU / Petra
            "pcu", "petra", "lifeatpcu", "petrachristian", "petrauniversity", "ukpetra",
            # UMS
            "ums", "umsofficial", "umsofficialid", "muhammadiyahsurakarta",
            # Generic
            "universitas", "univ", "kampus",
        }

        results = []
        for tag in vocabulary:
            if tag.lower() in univ_keywords:
                continue
            if any(kw in tag.lower() for kw in univ_keywords):
                continue

            score_data = score_map.get(tag, {})
            results.append({
                "hashtag": tag,
                "source": "historical",
                "viral_score": score_data.get("viral_score", 0),
                "avg_likes": score_data.get("avg_likes", 0),
                "avg_comments": score_data.get("avg_comments", 0),
                "lift": score_data.get("lift", 1.0),
                "post_count": score_data.get("post_count", 0),
                "reasoning": "Berdasarkan performa historis",
            })

        # Sort by viral score
        results.sort(key=lambda x: x.get("viral_score", 0), reverse=True)

        return results[:max_recommendations]


# Singleton instance
_sumopod_service = None


def get_sumopod_service() -> SumopodService:
    """Get atau create singleton instance dari SumopodService."""
    global _sumopod_service
    if _sumopod_service is None:
        _sumopod_service = SumopodService()
    return _sumopod_service
