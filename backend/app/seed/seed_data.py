"""
Seed data: 5 realistic university course descriptions for pre-loading.
"""

SEED_COURSES = [
    {
        "code": "CS101",
        "name": "Introduction to Computer Science",
        "department": "Computer Science",
        "credits": 6,
        "description": """Course Description
This course provides a broad introduction to the field of computer science. Students will learn foundational concepts in computing, problem-solving, and algorithmic thinking.

Learning Outcomes
1. Understand fundamental computing concepts including data representation and Boolean logic.
2. Design and implement simple algorithms using a high-level programming language.
3. Analyze the efficiency of basic algorithms.
4. Understand the basics of computer architecture and operating systems.

Course Content
Topics covered include: history of computing, binary and hexadecimal number systems, Boolean algebra, introduction to programming with Python, control structures (loops, conditionals), functions, basic data structures (lists, dictionaries), file I/O, introduction to object-oriented programming, and overview of computer networks.

Weekly Schedule
Week 1-2: History and fundamentals of computing
Week 3-4: Number systems and data representation
Week 5-6: Introduction to Python programming
Week 7: Midterm Exam
Week 8-9: Control structures and functions
Week 10-11: Data structures basics
Week 12-13: Object-oriented programming introduction
Week 14: Final review and project presentations

Assessment
Midterm Exam: 30%
Final Exam: 40%
Assignments: 20%
Class Participation: 10%

Textbooks
- "Computer Science: An Overview" by J. Glenn Brookshear
- "Python Crash Course" by Eric Matthes"""
    },
    {
        "code": "CS301",
        "name": "Data Structures and Algorithms",
        "department": "Computer Science",
        "credits": 6,
        "description": """Course Description
This course covers the design, analysis, and implementation of fundamental data structures and algorithms. Emphasis is on understanding the trade-offs between different data structures and their impact on algorithm performance.

Learning Outcomes
1. Implement and use fundamental data structures including arrays, linked lists, trees, heaps, hash tables, and graphs.
2. Analyze time and space complexity using Big-O notation.
3. Apply sorting and searching algorithms to solve computational problems.
4. Design algorithms using divide-and-conquer, greedy, and dynamic programming paradigms.
5. Select appropriate data structures for given problem scenarios.

Course Content
Arrays and linked lists, stacks and queues, binary trees and binary search trees, AVL trees, heaps and priority queues, hash tables, graph representations, graph traversals (BFS, DFS), shortest path algorithms (Dijkstra, Bellman-Ford), minimum spanning trees, sorting algorithms (merge sort, quicksort, heapsort), dynamic programming, greedy algorithms.

Weekly Schedule
Week 1: Review of arrays and complexity analysis
Week 2-3: Linked lists, stacks, queues
Week 4-5: Trees and binary search trees
Week 6: Heaps and priority queues
Week 7: Midterm Exam
Week 8: Hash tables and collision resolution
Week 9-10: Graph algorithms
Week 11-12: Sorting algorithms
Week 13: Dynamic programming
Week 14: Advanced topics and review

Assessment
Midterm Exam: 25%
Final Exam: 35%
Programming Assignments: 30%
Quizzes: 10%

Textbooks
- "Introduction to Algorithms" by Cormen, Leiserson, Rivest, Stein
- "Data Structures and Algorithm Analysis in C++" by Mark Allen Weiss"""
    },
    {
        "code": "CS420",
        "name": "Machine Learning",
        "department": "Computer Science",
        "credits": 6,
        "description": """Course Description
This course introduces the fundamental concepts and techniques of machine learning. Students will study supervised and unsupervised learning methods, learn to evaluate model performance, and apply ML techniques to real-world datasets.

Learning Outcomes
1. Understand the mathematical foundations of machine learning including probability, statistics, and linear algebra.
2. Implement supervised learning algorithms: linear regression, logistic regression, decision trees, SVM, and neural networks.
3. Implement unsupervised learning methods: k-means clustering, hierarchical clustering, and PCA.
4. Evaluate models using cross-validation, confusion matrices, ROC curves, and other metrics.
5. Apply feature engineering and data preprocessing techniques.

Course Content
Introduction to ML and types of learning. Probability and statistics review. Linear regression and gradient descent. Logistic regression and classification. Decision trees and random forests. Support vector machines. Neural networks and backpropagation. K-means and hierarchical clustering. Principal component analysis. Model evaluation and selection. Ensemble methods. Introduction to deep learning concepts.

Weekly Schedule
Week 1: Introduction to Machine Learning
Week 2: Probability and Statistics Review
Week 3-4: Linear and Logistic Regression
Week 5: Decision Trees and Random Forests
Week 6: Support Vector Machines
Week 7: Midterm Exam
Week 8-9: Neural Networks
Week 10: Clustering Methods
Week 11: Dimensionality Reduction (PCA)
Week 12: Model Selection and Evaluation
Week 13: Ensemble Methods
Week 14: Project Presentations

Assessment
Midterm Exam: 25%
Final Exam: 30%
Programming Projects: 35%
Paper Presentation: 10%

Textbooks
- "Pattern Recognition and Machine Learning" by Christopher Bishop
- "Hands-On Machine Learning" by Aurélien Géron"""
    },
    {
        "code": "CS350",
        "name": "Database Management Systems",
        "department": "Computer Science",
        "credits": 5,
        "description": """Course Description
This course covers the principles and practices of database management systems. Students will learn relational database design, SQL, transaction management, and modern database technologies.

Learning Outcomes
1. Design relational databases using ER diagrams and normalization techniques.
2. Write complex SQL queries including joins, subqueries, and aggregations.
3. Understand transaction management, concurrency control, and recovery mechanisms.
4. Implement database applications using a programming language with database connectivity.
5. Evaluate NoSQL database technologies and their use cases.

Course Content
Introduction to database systems, entity-relationship model, relational model, relational algebra, SQL (DDL, DML, DCL), normalization (1NF through BCNF), indexing and hashing, query processing and optimization, transaction management (ACID properties), concurrency control, database recovery, NoSQL databases introduction, and database security.

Weekly Schedule
Week 1: Introduction to Database Systems
Week 2-3: ER Model and Relational Model
Week 4-5: SQL Fundamentals and Advanced Queries
Week 6: Normalization
Week 7: Midterm Exam
Week 8: Indexing and Query Optimization
Week 9-10: Transaction Management and Concurrency
Week 11: Recovery and Security
Week 12-13: NoSQL and Modern Databases
Week 14: Project Presentations

Assessment
Midterm Exam: 25%
Final Exam: 30%
Database Project: 30%
Lab Exercises: 15%

Textbooks
- "Database System Concepts" by Silberschatz, Korth, Sudarshan
- "Fundamentals of Database Systems" by Elmasri and Navathe"""
    },
    {
        "code": "CS410",
        "name": "Natural Language Processing",
        "department": "Computer Science",
        "credits": 6,
        "description": """Course Description
This course provides a comprehensive introduction to natural language processing (NLP). Students will learn both traditional and modern deep learning approaches to processing and understanding human language.

Learning Outcomes
1. Understand linguistic fundamentals relevant to NLP: morphology, syntax, semantics, and pragmatics.
2. Implement text preprocessing pipelines: tokenization, stemming, lemmatization, and stopword removal.
3. Apply classical NLP techniques: TF-IDF, n-grams, and bag-of-words models.
4. Build NLP applications using word embeddings (Word2Vec, GloVe) and transformer-based models (BERT).
5. Develop systems for named entity recognition, sentiment analysis, text classification, and machine translation.

Course Content
Introduction to NLP and linguistic fundamentals. Text preprocessing and normalization. Language models and n-grams. Part-of-speech tagging. Named entity recognition. Word embeddings (Word2Vec, GloVe, FastText). Recurrent neural networks for NLP. Attention mechanisms and transformers. BERT and transfer learning for NLP. Sentiment analysis. Text classification. Machine translation. Question answering systems. Text summarization.

Weekly Schedule
Week 1: Introduction to NLP
Week 2: Text Preprocessing and Tokenization
Week 3: Language Models and N-grams
Week 4: POS Tagging and Named Entity Recognition
Week 5-6: Word Embeddings
Week 7: Midterm Exam
Week 8-9: RNNs, LSTMs, and Attention
Week 10-11: Transformers and BERT
Week 12: Sentiment Analysis and Text Classification
Week 13: Machine Translation and Summarization
Week 14: Project Presentations

Assessment
Midterm Exam: 20%
Final Exam: 30%
NLP Project: 35%
Paper Reviews: 15%

Textbooks
- "Speech and Language Processing" by Jurafsky and Martin
- "Natural Language Processing with Transformers" by Lewis Tunstall et al."""
    },
]
