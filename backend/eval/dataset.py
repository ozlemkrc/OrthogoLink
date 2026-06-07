"""
Labeled benchmark for evaluating orthogonality / overlap detection quality.

The benchmark has two parts:

* ``CATALOG`` — a set of "existing curriculum" courses that get embedded and
  indexed, exactly as a real catalog would be.
* ``QUERIES`` — proposed-course syllabi, each annotated with the set of catalog
  course codes it *genuinely overlaps* with (``expected_overlap``). Every other
  catalog course is, by construction, a true negative for that query.

The dataset is deliberately small but covers the cases that matter for grading:

* monolingual overlap (EN proposal vs EN catalog course),
* **cross-lingual** overlap (TR proposal vs EN catalog course, and vice versa) —
  the main justification for using a multilingual embedding model,
* a genuinely orthogonal proposal that should match nothing (guards against a
  threshold that is too lenient).

It is intended as a seed: add rows to make the precision/recall numbers more
robust. Keep ``expected_overlap`` conservative — only list pairs a human
curriculum reviewer would clearly call overlapping.
"""
from dataclasses import dataclass, field


@dataclass
class CatalogCourse:
    code: str
    name: str
    description: str
    university: str = "Local Seed Catalog"
    faculty: str = "Faculty of Engineering"
    department: str = "Computer Engineering"


@dataclass
class Query:
    name: str
    text: str
    expected_overlap: set[str] = field(default_factory=set)


# ── Existing curriculum ──────────────────────────────────────────

CATALOG: list[CatalogCourse] = [
    CatalogCourse(
        code="CS301",
        name="Data Structures and Algorithms",
        description=(
            "Course Content\n"
            "Arrays, linked lists, stacks, queues, trees, binary search trees, "
            "heaps, hash tables, and graphs. Sorting and searching algorithms, "
            "algorithm complexity analysis with big-O notation, recursion, "
            "divide and conquer, and dynamic programming.\n"
            "Learning Outcomes\n"
            "Students can select appropriate data structures, analyze time and "
            "space complexity, and implement efficient algorithms for searching, "
            "sorting, and graph traversal.\n"
        ),
    ),
    CatalogCourse(
        code="CS350",
        name="Database Management Systems",
        description=(
            "Course Content\n"
            "Relational data model, entity-relationship modeling, relational "
            "algebra, SQL query language, functional dependencies and "
            "normalization, indexing, transactions, concurrency control, and "
            "recovery.\n"
            "Learning Outcomes\n"
            "Students can design normalized relational schemas, write complex SQL "
            "queries, and reason about transaction isolation and indexing.\n"
        ),
    ),
    CatalogCourse(
        code="CS420",
        name="Machine Learning",
        description=(
            "Course Content\n"
            "Supervised and unsupervised learning, linear and logistic "
            "regression, decision trees, support vector machines, neural "
            "networks, clustering, regularization, overfitting, gradient "
            "descent, and model evaluation metrics.\n"
            "Learning Outcomes\n"
            "Students can train and evaluate predictive models, tune "
            "hyperparameters, and diagnose underfitting and overfitting.\n"
        ),
    ),
    CatalogCourse(
        code="CS410",
        name="Natural Language Processing",
        description=(
            "Course Content\n"
            "Text preprocessing, tokenization, word embeddings, language models, "
            "part-of-speech tagging, named entity recognition, sentiment "
            "analysis, machine translation, and transformer architectures.\n"
            "Learning Outcomes\n"
            "Students can build NLP pipelines, represent text as vectors, and "
            "apply neural sequence models to language tasks.\n"
        ),
    ),
    CatalogCourse(
        code="CS101",
        name="Introduction to Computer Science",
        description=(
            "Course Content\n"
            "Fundamentals of programming with Python, variables, data types, "
            "control flow, loops, functions, basic input and output, and "
            "elementary problem solving. Introduction to computational thinking.\n"
            "Learning Outcomes\n"
            "Students can write, debug, and run small Python programs using "
            "variables, conditionals, loops, and functions.\n"
        ),
    ),
    CatalogCourse(
        code="MATH201",
        name="Linear Algebra",
        description=(
            "Course Content\n"
            "Vectors, matrices, systems of linear equations, Gaussian "
            "elimination, vector spaces, linear independence, basis and "
            "dimension, determinants, eigenvalues, and eigenvectors.\n"
            "Learning Outcomes\n"
            "Students can solve linear systems, compute eigenvalues, and reason "
            "about vector spaces and linear transformations.\n"
        ),
        department="Mathematics",
        faculty="Faculty of Science",
    ),
    CatalogCourse(
        code="BBM104",
        name="Programlama Laboratuvarı",
        description=(
            "Ders İçeriği\n"
            "Python programlama diline giriş; değişkenler, veri tipleri, koşullu "
            "ifadeler, döngüler, fonksiyonlar, temel girdi çıktı işlemleri ve "
            "basit problem çözme teknikleri.\n"
            "Öğrenme Çıktıları\n"
            "Öğrenciler değişken, koşul, döngü ve fonksiyon kullanarak küçük "
            "Python programları yazabilir ve hatalarını ayıklayabilir.\n"
        ),
        university="Hacettepe Üniversitesi",
    ),
    CatalogCourse(
        code="BLM301",
        name="Veri Yapıları",
        description=(
            "Ders İçeriği\n"
            "Diziler, bağlı listeler, yığıtlar, kuyruklar, ağaçlar, ikili arama "
            "ağaçları, yığınlar, karma tabloları ve çizgeler. Sıralama ve arama "
            "algoritmaları, algoritma karmaşıklığı analizi ve özyineleme.\n"
            "Öğrenme Çıktıları\n"
            "Öğrenciler uygun veri yapısını seçebilir, zaman ve yer "
            "karmaşıklığını analiz edebilir ve verimli algoritmalar geliştirebilir.\n"
        ),
        university="Gebze Teknik Üniversitesi",
    ),
    CatalogCourse(
        code="EEE201",
        name="Circuit Theory",
        description=(
            "Course Content\n"
            "Kirchhoff's laws, nodal and mesh analysis, Thevenin and Norton "
            "equivalents, capacitors and inductors, transient analysis of RC and "
            "RL circuits, and sinusoidal steady-state AC analysis.\n"
            "Learning Outcomes\n"
            "Students can analyze linear electrical circuits in the time and "
            "frequency domains.\n"
        ),
        department="Electrical Engineering",
    ),
    CatalogCourse(
        code="IST220",
        name="Probability and Statistics",
        description=(
            "Course Content\n"
            "Sample spaces, probability axioms, conditional probability, random "
            "variables, common probability distributions, expectation and "
            "variance, the central limit theorem, estimation, confidence "
            "intervals, and hypothesis testing.\n"
            "Learning Outcomes\n"
            "Students can model uncertainty with random variables and perform "
            "basic statistical inference.\n"
        ),
        department="Statistics",
        faculty="Faculty of Science",
    ),
]


# ── Proposed-course syllabi with ground-truth overlap labels ─────

QUERIES: list[Query] = [
    Query(
        name="Algorithms & Data Structures (EN proposal)",
        text=(
            "Course Content\n"
            "This course covers fundamental data structures including linked "
            "lists, stacks, queues, trees, balanced search trees, heaps, hash "
            "tables, and graphs. It develops algorithms for sorting, searching, "
            "and graph traversal, and teaches asymptotic complexity analysis, "
            "recursion, and dynamic programming.\n"
            "Learning Outcomes\n"
            "Students will analyze algorithmic complexity and choose suitable "
            "data structures to solve computational problems efficiently.\n"
        ),
        # Overlaps both the EN and the TR data-structures course (cross-lingual).
        expected_overlap={"CS301", "BLM301"},
    ),
    Query(
        name="Makine Öğrenmesine Giriş (TR proposal)",
        text=(
            "Ders İçeriği\n"
            "Denetimli ve denetimsiz öğrenme, doğrusal ve lojistik regresyon, "
            "karar ağaçları, destek vektör makineleri, yapay sinir ağları, "
            "kümeleme, aşırı öğrenme, gradyan iniş ve model değerlendirme "
            "ölçütleri.\n"
            "Öğrenme Çıktıları\n"
            "Öğrenciler tahmin modelleri eğitip değerlendirebilir ve aşırı "
            "öğrenmeyi teşhis edebilir.\n"
        ),
        # TR proposal overlapping an EN catalog course (cross-lingual).
        expected_overlap={"CS420"},
    ),
    Query(
        name="Relational Databases & SQL (EN proposal)",
        text=(
            "Course Content\n"
            "Relational model, ER diagrams, relational algebra, structured query "
            "language SQL, normalization and functional dependencies, indexing, "
            "transactions, and concurrency control.\n"
            "Learning Outcomes\n"
            "Students will design relational schemas and write SQL queries over "
            "normalized databases.\n"
        ),
        expected_overlap={"CS350"},
    ),
    Query(
        name="Introduction to Programming with Python (EN proposal)",
        text=(
            "Course Content\n"
            "Basics of programming using Python: variables, primitive data "
            "types, conditional statements, loops, functions, and simple input "
            "and output. Emphasis on computational thinking and debugging.\n"
            "Learning Outcomes\n"
            "Students will write and debug small Python programs.\n"
        ),
        # Overlaps the EN intro course and the TR programming-lab course.
        expected_overlap={"CS101", "BBM104"},
    ),
    Query(
        name="Olasılık ve İstatistik (TR proposal)",
        text=(
            "Ders İçeriği\n"
            "Örnek uzayları, olasılık aksiyomları, koşullu olasılık, rastgele "
            "değişkenler, olasılık dağılımları, beklenen değer ve varyans, merkezi "
            "limit teoremi, güven aralıkları ve hipotez testi.\n"
            "Öğrenme Çıktıları\n"
            "Öğrenciler belirsizliği rastgele değişkenlerle modelleyip temel "
            "istatistiksel çıkarım yapabilir.\n"
        ),
        expected_overlap={"IST220"},
    ),
    Query(
        name="Marine Biology of Coral Reefs (orthogonal control)",
        text=(
            "Course Content\n"
            "Coral reef ecosystems, marine biodiversity, symbiosis between coral "
            "and algae, ocean acidification, reef conservation, and the ecology "
            "of tropical marine invertebrates and fish populations.\n"
            "Learning Outcomes\n"
            "Students will describe reef ecosystem dynamics and threats to marine "
            "biodiversity.\n"
        ),
        # Should overlap nothing in an engineering/science CS catalog.
        expected_overlap=set(),
    ),
]
