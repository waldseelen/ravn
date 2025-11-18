# Projeye Katk─▒ Sa─şlama (Contributing)

## Ho┼ş Geldiniz! ­şæï

RAVN projesine katk─▒ sa─şlamakla ilgilenmedi─şiniz i├ğin te┼şekk├╝rler! Bu dok├╝mantasyon, size nas─▒l etkili bir ┼şekilde proje geli┼ştirmeye kat─▒labilece─şinizi g├Âsterecektir.

---

## Ba┼şlamadan ├ûnce

1. **Projeyi Fork'lay─▒n:** GitHub'da "Fork" butonu ile kendi hesab─▒n─▒za kopya olu┼şturun
2. **Repoyu klonlay─▒n:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/ravn.git
   cd ravn
   ```
3. **Upstream kurulumu:**
   ```bash
   git remote add upstream https://github.com/waldseelen/ravn.git
   ```

---

## Geli┼ştirme Ortam─▒ Kurulumu

### Gereksinimler
- Python 3.8 veya daha y├╝ksek
- FFmpeg (sistem PATH'inde veya proje dizininde)
- Git

### Kurulum Ad─▒mlar─▒

```bash
# Virtual environment olu┼ştur
python -m venv venv

# Virtual environment'i aktive et
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Ba─ş─▒ml─▒l─▒klar─▒ kur
pip install -r requirements.txt

# Geli┼ştirme ara├ğlar─▒n─▒ kur
pip install pytest pytest-cov black flake8 pylint
```

### Testleri ├çal─▒┼şt─▒r

```bash
# T├╝m testleri ├ğal─▒┼şt─▒r
pytest tests/ -v

# Coverage raporu ile ├ğal─▒┼şt─▒r
pytest tests/ --cov=ravn_app --cov-report=html

# Belirli test dosyas─▒n─▒ ├ğal─▒┼şt─▒r
pytest tests/test_core.py -v

# Belirli test fonksiyonunu ├ğal─▒┼şt─▒r
pytest tests/test_core.py::TestYouTubeDownloader::test_format_options -v
```

---

## Katk─▒ T├╝rleri

### 1. Bug Raporu

Bir bug buldunuz mu? GitHub Issues'de bir rapor a├ğ─▒n:

**Bug raporu ┼şablonu:**
```
**A├ğ─▒klama:** Bug'─▒n k─▒sa a├ğ─▒klamas─▒

**Ad─▒mlar─▒ Tekrarla:**
1. ...
2. ...
3. ...

**Beklenen Davran─▒┼ş:** Ne olmas─▒ gerekiyordu?

**Ger├ğek Davran─▒┼ş:** Ne oldu?

**Ortam:**
- OS: [├Âr: Windows 10]
- Python: [├Âr: 3.11.0]
- RAVN: [├Âr: v1.0.0]
```

### 2. ├ûzellik Talebi (Feature Request)

Yeni bir ├Âzellik ├Ânerisini Issues'de a├ğ─▒n:

**├ûzellik talebinin ┼şablonu:**
```
**A├ğ─▒klama:** Yeni ├Âzelli─şin ne oldu─şunu a├ğ─▒klay─▒n

**Ama├ğ:** Bu ├Âzellik ne sorunu ├ğ├Âzer?

**├ûnerilen ├ç├Âz├╝m:** Nas─▒l ├ğal─▒┼şmas─▒ gerekir?

**Alternatif ├ç├Âz├╝mler:** Ba┼şka se├ğenekler var m─▒?
```

### 3. Kod Katk─▒s─▒

Kod yazarak projeye katk─▒ sa─şlamak istiyorsan─▒z:

#### Ad─▒m 1: Issue'yi Belirleyin

- A├ğ─▒k bir issue'yi se├ğin ve yorum yazarak ├╝zerinde ├ğal─▒┼şaca─ş─▒n─▒z─▒ belirtin
- Kendi issue'nizi a├ğabilirsiniz (b├╝y├╝k de─şi┼şiklikler i├ğin ├Ânerilir)

#### Ad─▒m 2: Branch Olu┼şturun

```bash
# En son develop'─▒ ├ğek
git fetch upstream
git checkout develop

# Yeni feature branch olu┼ştur
git checkout -b feature/your-feature-name

# veya bug branch'i
git checkout -b bugfix/your-bug-fix
```

**Branch Adland─▒rma:**
- Feature: `feature/video-converter`
- Bug: `bugfix/download-error`
- Dok├╝mantasyon: `docs/setup-guide`
- Refactor: `refactor/module-structure`

#### Ad─▒m 3: Kod Yaz─▒n

**Kod Stil Rehberi:**
- PEP 8 standard─▒n─▒ takip edin
- Maksimum sat─▒r uzunlu─şu: 100 karakter
- Anla┼ş─▒l─▒r de─şi┼şken isimleri kullan─▒n
- Fonksiyonlara docstring ekleyin

**Docstring ├ûrne─şi:**
```python
def download_video(url: str, output_path: str) -> bool:
    """
    YouTube videosunu indir.
    
    Args:
        url (str): Video URL'si
        output_path (str): ─░ndirilen dosya yolu
    
    Returns:
        bool: ─░┼şlem ba┼şar─▒l─▒ ise True
    
    Raises:
        ValueError: URL ge├ğersiz ise
    """
```

#### Ad─▒m 4: Testler Yaz─▒n

Her feature veya bug fix i├ğin test yaz─▒n:

```python
def test_new_feature():
    """Test the new feature."""
    # Arrange
    input_data = ...
    
    # Act
    result = feature_function(input_data)
    
    # Assert
    assert result == expected_value
```

#### Ad─▒m 5: Kodu Formatla

```bash
# Black ile formatla
black ravn_app tests

# isort ile import'lar─▒ d├╝zenle
isort ravn_app tests

# Linting kontrol
flake8 ravn_app tests
```

#### Ad─▒m 6: Commit Yap

```bash
# De─şi┼şiklikleri stage et
git add .

# Commit yap (Conventional Commits kullanarak)
git commit -m "feat: Add new feature description

- Implementation detail 1
- Implementation detail 2

Fixes #123"
```

**Commit Mesaj─▒ Format─▒:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**T├╝r ├ûrnekleri:**
- `feat`: Yeni ├Âzellik
- `fix`: Bug d├╝zeltme
- `docs`: Dok├╝mantasyon
- `style`: Kod stili
- `refactor`: Yeniden yap─▒land─▒rma
- `test`: Test ekleme
- `chore`: Build/dependencies

#### Ad─▒m 7: Push Et

```bash
git push origin feature/your-feature-name
```

#### Ad─▒m 8: Pull Request (PR) A├ğ

1. GitHub'da "New Pull Request" t─▒klay─▒n
2. **Base:** `develop` (├Âzellikler)
3. **Head:** Sizin branch'iniz
4. PR ┼şablonunu doldurun:

```markdown
## A├ğ─▒klama
Yapt─▒─ş─▒n─▒z de─şi┼şiklikleri a├ğ─▒klay─▒n.

## ─░lgili Issue
Fixes #123

## De─şi┼şiklikler
- [ ] ├ûzellik A eklendi
- [ ] Bug B d├╝zeltildi
- [ ] Dok├╝mantasyon g├╝ncellendi

## Test Edildi
- [ ] Birim testleri ge├ğti
- [ ] Manuel test yap─▒ld─▒

## Checklist
- [ ] Kodu self-review ettim
- [ ] Uygun yorumlar ve docstring ekledim
- [ ] Dok├╝mantasyonu g├╝ncelledim
- [ ] Yeni testler ekledim
- [ ] T├╝m testler ge├ğti
```

---

## Kod ─░ncelemesi (Code Review) S├╝reci

### Reviewer'lar ─░├ğin

1. **Kod Kalitesi:** Okunabilir, verimli mi?
2. **Testler:** T├╝m testler ge├ğiyor mu? Coverage yeterli mi?
3. **Dok├╝mantasyon:** Kod dok├╝mante edilmi┼ş mi?
4. **Performans:** Performance problem var m─▒?
5. **G├╝venlik:** G├╝venlik a├ğ─▒─ş─▒ var m─▒?

### Contributor'lar ─░├ğin

Ele┼ştiri al─▒rsan─▒z:
- Ki┼şisel al─▒nmay─▒n - kod kalitesi i├ğin yap─▒l─▒r
- A├ğ─▒klamalar isterse, sorular sorun
- Feedback'a dayanarak h─▒zl─▒ bir ┼şekilde d├╝zeltme yap─▒n

---

## CI/CD Pipeline

T├╝m PR'lar otomatik olarak test edilen:

1. **Tests:** `pytest tests/ --cov=ravn_app`
2. **Linting:** `flake8`, `black`, `isort`
3. **Build:** PyInstaller (main branch'i i├ğin)

Pipeline ge├ğmezse, sorunlar─▒ d├╝zeltip push edin - otomatik olarak yeniden ├ğal─▒┼şacak.

---

## Dok├╝mantasyon Katk─▒lar─▒

Dok├╝mantasyon g├╝ncellemeleri i├ğin:

1. Dosyay─▒ edit edin
2. Test edin (link kontrol├╝, format─▒)
3. PR a├ğ─▒n (`docs/` prefix'i ile)

**Markdown Stil:**
- Ba┼şl─▒klar: `#` (H1), `##` (H2), vb.
- Kod blo─şu: ` ```python ... ``` `
- Link: `[Text](url)`
- Liste: `-` veya `*`

---

## Sorular & Destek

- **Bug raporu:** GitHub Issues a├ğ─▒n
- **├ûzellik talebine:** GitHub Issues'de tart─▒┼ş─▒n
- **Teknik soru:** Issue ba┼şl─▒─ş─▒nda `[QUESTION]` kullan─▒n

---

## Te┼şekk├╝rler ­şÖÅ

Projeye katk─▒ sa─şlad─▒─ş─▒n─▒z i├ğin te┼şekk├╝rler! Sizin i┼şbirli─şiniz RAVN'─▒ daha iyi hale getiriyor.

**Happy coding!** ­şÜÇ
