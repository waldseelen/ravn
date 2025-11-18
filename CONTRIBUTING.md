# Projeye Katkı Sağlama (Contributing)

## Hoş Geldiniz! 👋

RAVN projesine katkı sağlamakla ilgilenmediğiniz için teşekkürler! Bu dokümantasyon, size nasıl etkili bir şekilde proje geliştirmeye katılabileceğinizi gösterecektir.

---

## Başlamadan Önce

1. **Projeyi Fork'layın:** GitHub'da "Fork" butonu ile kendi hesabınıza kopya oluşturun
2. **Repoyu klonlayın:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/ravn.git
   cd ravn
   ```
3. **Upstream kurulumu:**
   ```bash
   git remote add upstream https://github.com/waldseelen/ravn.git
   ```

---

## Geliştirme Ortamı Kurulumu

### Gereksinimler
- Python 3.8 veya daha yüksek
- FFmpeg (sistem PATH'inde veya proje dizininde)
- Git

### Kurulum Adımları

```bash
# Virtual environment oluştur
python -m venv venv

# Virtual environment'i aktive et
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Bağımlılıkları kur
pip install -r requirements.txt

# Geliştirme araçlarını kur
pip install pytest pytest-cov black flake8 pylint
```

### Testleri Çalıştır

```bash
# Tüm testleri çalıştır
pytest tests/ -v

# Coverage raporu ile çalıştır
pytest tests/ --cov=ravn_app --cov-report=html

# Belirli test dosyasını çalıştır
pytest tests/test_core.py -v

# Belirli test fonksiyonunu çalıştır
pytest tests/test_core.py::TestYouTubeDownloader::test_format_options -v
```

---

## Katkı Türleri

### 1. Bug Raporu

Bir bug buldunuz mu? GitHub Issues'de bir rapor açın:

**Bug raporu şablonu:**
```
**Açıklama:** Bug'ın kısa açıklaması

**Adımları Tekrarla:**
1. ...
2. ...
3. ...

**Beklenen Davranış:** Ne olması gerekiyordu?

**Gerçek Davranış:** Ne oldu?

**Ortam:**
- OS: [ör: Windows 10]
- Python: [ör: 3.11.0]
- RAVN: [ör: v1.0.0]
```

### 2. Özellik Talebi (Feature Request)

Yeni bir özellik önerisini Issues'de açın:

**Özellik talebinin şablonu:**
```
**Açıklama:** Yeni özelliğin ne olduğunu açıklayın

**Amaç:** Bu özellik ne sorunu çözer?

**Önerilen Çözüm:** Nasıl çalışması gerekir?

**Alternatif Çözümler:** Başka seçenekler var mı?
```

### 3. Kod Katkısı

Kod yazarak projeye katkı sağlamak istiyorsanız:

#### Adım 1: Issue'yi Belirleyin

- Açık bir issue'yi seçin ve yorum yazarak üzerinde çalışacağınızı belirtin
- Kendi issue'nizi açabilirsiniz (büyük değişiklikler için önerilir)

#### Adım 2: Branch Oluşturun

```bash
# En son develop'ı çek
git fetch upstream
git checkout develop

# Yeni feature branch oluştur
git checkout -b feature/your-feature-name

# veya bug branch'i
git checkout -b bugfix/your-bug-fix
```

**Branch Adlandırma:**
- Feature: `feature/video-converter`
- Bug: `bugfix/download-error`
- Dokümantasyon: `docs/setup-guide`
- Refactor: `refactor/module-structure`

#### Adım 3: Kod Yazın

**Kod Stil Rehberi:**
- PEP 8 standardını takip edin
- Maksimum satır uzunluğu: 100 karakter
- Anlaşılır değişken isimleri kullanın
- Fonksiyonlara docstring ekleyin

**Docstring Örneği:**
```python
def download_video(url: str, output_path: str) -> bool:
    """
    YouTube videosunu indir.
    
    Args:
        url (str): Video URL'si
        output_path (str): İndirilen dosya yolu
    
    Returns:
        bool: İşlem başarılı ise True
    
    Raises:
        ValueError: URL geçersiz ise
    """
```

#### Adım 4: Testler Yazın

Her feature veya bug fix için test yazın:

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

#### Adım 5: Kodu Formatla

```bash
# Black ile formatla
black ravn_app tests

# isort ile import'ları düzenle
isort ravn_app tests

# Linting kontrol
flake8 ravn_app tests
```

#### Adım 6: Commit Yap

```bash
# Değişiklikleri stage et
git add .

# Commit yap (Conventional Commits kullanarak)
git commit -m "feat: Add new feature description

- Implementation detail 1
- Implementation detail 2

Fixes #123"
```

**Commit Mesajı Formatı:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Tür Örnekleri:**
- `feat`: Yeni özellik
- `fix`: Bug düzeltme
- `docs`: Dokümantasyon
- `style`: Kod stili
- `refactor`: Yeniden yapılandırma
- `test`: Test ekleme
- `chore`: Build/dependencies

#### Adım 7: Push Et

```bash
git push origin feature/your-feature-name
```

#### Adım 8: Pull Request (PR) Aç

1. GitHub'da "New Pull Request" tıklayın
2. **Base:** `develop` (özellikler)
3. **Head:** Sizin branch'iniz
4. PR şablonunu doldurun:

```markdown
## Açıklama
Yaptığınız değişiklikleri açıklayın.

## İlgili Issue
Fixes #123

## Değişiklikler
- [ ] Özellik A eklendi
- [ ] Bug B düzeltildi
- [ ] Dokümantasyon güncellendi

## Test Edildi
- [ ] Birim testleri geçti
- [ ] Manuel test yapıldı

## Checklist
- [ ] Kodu self-review ettim
- [ ] Uygun yorumlar ve docstring ekledim
- [ ] Dokümantasyonu güncelledim
- [ ] Yeni testler ekledim
- [ ] Tüm testler geçti
```

---

## Kod İncelemesi (Code Review) Süreci

### Reviewer'lar İçin

1. **Kod Kalitesi:** Okunabilir, verimli mi?
2. **Testler:** Tüm testler geçiyor mu? Coverage yeterli mi?
3. **Dokümantasyon:** Kod dokümante edilmiş mi?
4. **Performans:** Performance problem var mı?
5. **Güvenlik:** Güvenlik açığı var mı?

### Contributor'lar İçin

Eleştiri alırsanız:
- Kişisel alınmayın - kod kalitesi için yapılır
- Açıklamalar isterse, sorular sorun
- Feedback'a dayanarak hızlı bir şekilde düzeltme yapın

---

## CI/CD Pipeline

Tüm PR'lar otomatik olarak test edilen:

1. **Tests:** `pytest tests/ --cov=ravn_app`
2. **Linting:** `flake8`, `black`, `isort`
3. **Build:** PyInstaller (main branch'i için)

Pipeline geçmezse, sorunları düzeltip push edin - otomatik olarak yeniden çalışacak.

---

## Dokümantasyon Katkıları

Dokümantasyon güncellemeleri için:

1. Dosyayı edit edin
2. Test edin (link kontrolü, formatı)
3. PR açın (`docs/` prefix'i ile)

**Markdown Stil:**
- Başlıklar: `#` (H1), `##` (H2), vb.
- Kod bloğu: ` ```python ... ``` `
- Link: `[Text](url)`
- Liste: `-` veya `*`

---

## Sorular & Destek

- **Bug raporu:** GitHub Issues açın
- **Özellik talebine:** GitHub Issues'de tartışın
- **Teknik soru:** Issue başlığında `[QUESTION]` kullanın

---

## Teşekkürler 🙏

Projeye katkı sağladığınız için teşekkürler! Sizin işbirliğiniz RAVN'ı daha iyi hale getiriyor.

**Happy coding!** 🚀
