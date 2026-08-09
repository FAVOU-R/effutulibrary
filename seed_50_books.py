import sys, os
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import Book, BookCopy, Branch

def seed_50_books():
    db = SessionLocal()
    try:
        branches = db.query(Branch).all()
        if not branches:
            print("[SEED] No branches found. Please ensure database is initialized.")
            return

        main_branch_id = branches[0].id

        books_data = [
            # --- 1. Story Books & African Literature ---
            {
                "title": "Tales of Ananse the Spider",
                "author": "Efua Sutherland",
                "isbn": "9789988100011",
                "category": "Story Books & Literature",
                "publisher": "Ghana Publishing Corporation",
                "pub_year": 1975,
                "cover_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400",
                "description": "Classic Ghanaian folktales about Kwaku Ananse, the trickster spider, embodying wisdom, wit, and cultural satire.",
                "content_text": """CHAPTER 1: Ananse and the Sticky Rubber Doll
Long ago in the coastal kingdom of Winneba, Kwaku Ananse decided he wanted to own all the wisdom in the world. He gathered every proverbs, trick, and strategy into a small clay pot.

'If I keep this pot at the top of the tallest Baobab tree,' Ananse thought, 'no one else in Effutu land will ever outsmart me!'

He tied the pot around his stomach and tried to climb the tree. But because the pot was in front of him, his arms could not reach around the trunk. His young son, Ntikuma, stood watching from below.

'Father,' Ntikuma called out, 'why don't you tie the pot to your back? That way your arms will be free to climb.'

Ananse stopped. He realized his young son was already wiser than him! Frustrated, he threw the pot down. It smashed into pieces on the rocks, and wisdom scattered to all four corners of the Earth. And that is why today, wisdom belongs to everyone."""
            },
            {
                "title": "The Marriage of Anansewa",
                "author": "Efua Sutherland",
                "isbn": "9789988100028",
                "category": "Story Books & Literature",
                "publisher": "Sedco Publishing Ghana",
                "pub_year": 1980,
                "cover_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400",
                "description": "Anansewa's father tries to secure wealthy suitors for his daughter using classic trickery and Ghanaian dramatic flair.",
                "content_text": """ACT 1: The Outdooring of Anansewa
ANANSE: (Pacing the stage with a feather pen) Money! To be in financial distress is a terrible disease in Accra. But Kwaku Ananse does not die of poverty while his brain is active!

ANANSEWA: Father, why are you typing so fast on that old typewriter?

ANANSE: My daughter, I am writing to four great Chiefs of the country—Chief of Sape, Chief of Akwamu, Chief of Togoland, and Chief of the Mines! I am offering your hand in marriage to all four!

ANANSEWA: (Gasping) All four at the same time?!

ANANSE: Trust your father. They will send gifts, dowry, and gold to our house before any of them realizes the secret!"""
            },
            {
                "title": "The Cockcrow: West African Anthology",
                "author": "J. A. Anquandah & K. E. Senanu",
                "isbn": "9789988100035",
                "category": "Story Books & Literature",
                "publisher": "Afram Publications Ghana",
                "pub_year": 1995,
                "cover_url": "https://images.unsplash.com/photo-1476275466078-4007374efbbe?w=400",
                "description": "Essential Ghanaian JHS & SHS prose, poetry, and traditional storytelling collection approved by Ghana Education Service.",
                "content_text": """SELECTION: The Village Schoolmaster
Beside yon straggling fence that skirts the way,
With blossomed furze unprofitably gay,
There, in his noisy mansion, skilled to rule,
The village master taught his little school.

A man severe he was, and stern to view;
I knew him well, and every truant knew;
Well had the boding tremblers learned to trace
The day's disasters in his morning face."""
            },
            {
                "title": "The Beautyful Ones Are Not Yet Born",
                "author": "Ayi Kwei Armah",
                "isbn": "9780435905408",
                "category": "Story Books & Literature",
                "publisher": "Heinemann African Writers",
                "pub_year": 1968,
                "cover_url": "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400",
                "description": "A powerful Ghanaian novel detailing moral integrity, political transition, and societal change in post-independence Ghana.",
                "content_text": """CHAPTER 1: The Railway Station at Sekondi
The bus was old and smelled of stale diesel exhaust and damp leather. The driver pressed the starter button again, and the engine shuddered into life with a heavy metallic cough.

The Man sat near the back window, watching the street lamps flicker against the misty Ghanaian morning air. People rushed past holding wooden trays of fried plantain and roasted groundnuts.

'Why do you refuse to take the extra cedi?' his wife had asked him the previous night.

'Because a clean hand does not fear the morning sun,' the Man replied softly."""
            },
            {
                "title": "Efuru & The River Goddess",
                "author": "Flora Nwapa",
                "isbn": "9780435905002",
                "category": "Story Books & Literature",
                "publisher": "Heinemann",
                "pub_year": 1966,
                "cover_url": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400",
                "description": "A pioneering West African literary masterpiece celebrating female independence, dignity, and cultural tradition.",
                "content_text": """CHAPTER 1: Efuru's Trade
Efuru was a woman of noble birth, wealthy in her own right, and admired by everyone in Oguta. She was commanding, fiercely independent, and possessed a heart of generosity.

When she traveled to the market at Onitsha, merchants hailed her from afar. She traded in palm oil, textiles, and local spices. Yet despite her riches, Efuru sought peace of mind above all material wealth."""
            },
            {
                "title": "The Concubine",
                "author": "Elechi Amadi",
                "isbn": "9780435900250",
                "category": "Story Books & Literature",
                "publisher": "Heinemann African Writers",
                "pub_year": 1966,
                "cover_url": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=400",
                "description": "An enchanting story of love, destiny, and traditional African cosmology in a harmonious village community.",
                "content_text": """CHAPTER 1: Ihouma's Grace
Ihouma was a woman of extraordinary beauty and gentle spirit. Her presence brought calm wherever she walked in Omokachi village. Young men composed songs in her praise, and elders consulted her on matters of peace."""
            },
            {
                "title": "Abina and the Important Men",
                "author": "Trevor R. Getz & Liz Clarke",
                "isbn": "9780199846245",
                "category": "Story Books & Literature",
                "publisher": "Oxford University Press",
                "pub_year": 2012,
                "cover_url": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=400",
                "description": "A graphic history of a courageous woman who fought for her freedom in 1876 Cape Coast, Gold Coast (Ghana).",
                "content_text": """COURT TRANSCRIPT: Cape Coast Courthouse, 1876
MAGISTRATE: State your name for the record.
ABINA: My name is Abina Mansah. I was brought from the interior against my will.
MAGISTRATE: Did you work without pay?
ABINA: Yes. I cooked, swept, and fetched water from dawn till night. But I am a free woman under the laws of the Protectorate, and I demand my liberty!"""
            },
            {
                "title": "Changes: A Love Story",
                "author": "Ama Ata Aidoo",
                "isbn": "9780435909611",
                "category": "Story Books & Literature",
                "publisher": "The Women's Press",
                "pub_year": 1991,
                "cover_url": "https://images.unsplash.com/photo-1474939557374-9542446e5b77?w=400",
                "description": "Ghanaian feminist classic exploring modern career women, marriage, independence, and choices in contemporary Accra.",
                "content_text": """CHAPTER 1: Esi's Morning Routine
Esi Sekyi drove her Peugeot through the bustling traffic of Kwame Nkrumah Circle. The morning sun was just rising over the Ministry of Statistics. As a senior data analyst, her days were packed with urban demographic surveys."""
            },
            {
                "title": "The Dilemma of a Ghost",
                "author": "Ama Ata Aidoo",
                "isbn": "9780435901004",
                "category": "Story Books & Literature",
                "publisher": "Longman Ghana",
                "pub_year": 1965,
                "cover_url": "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=400",
                "description": "A dramatic clash between traditional Ghanaian family expectations and African-American heritage when Ato returns home with Eulalie.",
                "content_text": """ACT 1: The Return to Odetna
FIRST WOMAN: Have you heard? The son of the clan has returned from across the salt ocean!
SECOND WOMAN: Ato! He has completed his university education in America! But they say he brought home a wife who does not know how to prepare Fante kenkey!"""
            },
            {
                "title": "Burning Grass",
                "author": "Cyprian Ekwensi",
                "isbn": "9780435900021",
                "category": "Story Books & Literature",
                "publisher": "Heinemann",
                "pub_year": 1962,
                "cover_url": "https://images.unsplash.com/photo-1516979187457-637abb4f9353?w=400",
                "description": "A thrilling adventure of wanderlust, pastoral traditions, courage, and family ties across West African grasslands.",
                "content_text": """CHAPTER 1: The Sokugo Spell
When the dry harmattan wind blows across the savannas, the grass turns golden yellow and burns easily under the blazing sun. Mai Sunsaye felt the mysterious call of the Sokugo—the wandering sickness."""
            },

            # --- 2. Popular Mathematics ---
            {
                "title": "WASSCE Core Mathematics for Senior High Schools",
                "author": "Prof. J. A. Aryeetey & K. O. Mensah",
                "isbn": "9789988123028",
                "category": "Mathematics",
                "publisher": "Ghana Universities Press",
                "pub_year": 2023,
                "cover_url": "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=400",
                "description": "Full algebra, trigonometry, geometry, quadratic equations, and statistics textbook for WASSCE candidates in Ghana.",
                "content_text": """UNIT 3: Quadratic Equations & Simultaneous Functions
A quadratic equation is any polynomial equation of degree 2 written in the standard form:
ax² + bx + c = 0 (where a ≠ 0)

1. Solving by Quadratic Formula:
x = [-b ± √(b² - 4ac)] / (2a)

EXAMPLE 1 (WASSCE 2022 Question):
Solve 2x² - 7x + 3 = 0.
Solution:
a = 2, b = -7, c = 3
b² - 4ac = (-7)² - 4(2)(3) = 49 - 24 = 25
x = [7 ± √25] / 4 = (7 ± 5)/4
x = 12/4 = 3 OR x = 2/4 = 0.5.

2. Trigonometric Ratios (SOH CAH TOA):
Sin(θ) = Opposite / Hypotenuse
Cos(θ) = Adjacent / Hypotenuse
Tan(θ) = Opposite / Adjacent"""
            },
            {
                "title": "BECE Core Mathematics for Junior High Schools",
                "author": "S. A. Bosomtwe",
                "isbn": "9789988140019",
                "category": "Mathematics",
                "publisher": "Asempa Publishers Ghana",
                "pub_year": 2022,
                "cover_url": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=400",
                "description": "Comprehensive JHS 1-3 mathematics guide aligned with National Council for Curriculum and Assessment (NaCCA).",
                "content_text": """CHAPTER 5: Sets & Venn Diagrams
A set is a well-defined collection of distinct objects called elements.

Notation:
n(A) = Number of elements in set A
A ∩ B = Intersection of A and B (elements in both A and B)
A ∪ B = Union of A and B (elements in A or B or both)

Formula for two intersecting sets:
n(A ∪ B) = n(A) + n(B) - n(A ∩ B)

PRACTICE PROBLEM:
In a class of 40 students at Winneba Basic School, 25 play Football, 20 play Volleyball, and 8 play both games.
How many students play neither game?
Solution:
Total n(U) = 40
n(F) = 25, n(V) = 20, n(F ∩ V) = 8
n(F ∪ V) = 25 + 20 - 8 = 37
Neither = 40 - 37 = 3 students."""
            },
            {
                "title": "Elective Mathematics for SHS (Vol. 1 & 2)",
                "author": "J. K. Annan & E. K. Amponsah",
                "isbn": "9789988140026",
                "category": "Mathematics",
                "publisher": "Sedco Publishing",
                "pub_year": 2021,
                "cover_url": "https://images.unsplash.com/photo-1596495578065-6e0763fa1178?w=400",
                "description": "Advanced calculus, vectors, coordinate geometry, mechanics, and matrices for SHS science and engineering students.",
                "content_text": """CHAPTER 12: Differential Calculus
The derivative of a function y = f(x) represents the instantaneous rate of change of y with respect to x.

Power Rule:
If y = axⁿ, then dy/dx = n · a · xⁿ⁻¹

Example:
Find the derivative of y = 4x³ - 5x² + 7x - 9.
dy/dx = 4(3x²) - 5(2x) + 7(1) - 0
dy/dx = 12x² - 10x + 7."""
            },
            {
                "title": "Plane Geometry & Trigonometry Guide",
                "author": "E. K. Amponsah",
                "isbn": "9789988140033",
                "category": "Mathematics",
                "publisher": "Ghana Educational Series",
                "pub_year": 2020,
                "cover_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=400",
                "description": "Step-by-step proofs of circle theorems, mensuration of 3D solids, bearings, and locus for Ghanaian examinations.",
                "content_text": """CIRCLE THEOREM 1: Angle Subtended at the Center
The angle subtended by an arc at the center of a circle is double the angle subtended by it at any point on the circumference.

CIRCLE THEOREM 2: Angles in the Same Segment
Angles subtended by the same arc in the same segment of a circle are equal (∠APB = ∠AQB)."""
            },
            {
                "title": "Quantitative Aptitude & Logic for Students",
                "author": "Kwame Appiah",
                "isbn": "9789988140040",
                "category": "Mathematics",
                "publisher": "Accra Academic Press",
                "pub_year": 2023,
                "cover_url": "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=400",
                "description": "Problem-solving techniques, numerical reasoning, speed math, and logical puzzles for academic competitions.",
                "content_text": """SECTION 1: Number Series & Speed Multiplication
Shortcut for multiplying numbers near 100:
Multiply 96 × 97:
96 is (-4) below 100
97 is (-3) below 100
First digits: 96 - 3 = 93
Last digits: (-4) × (-3) = 12
Result = 9312."""
            },
            {
                "title": "Statistics & Probability for Ghanaian Colleges",
                "author": "Dr. Yaw Boateng",
                "isbn": "9789988140057",
                "category": "Mathematics",
                "publisher": "KNUST Press Kumasi",
                "pub_year": 2022,
                "cover_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400",
                "description": "Data representation, standard deviation, variance, binomial distribution, and hypothesis testing with local case studies.",
                "content_text": """CHAPTER 4: Measures of Central Tendency & Dispersion
Mean (x̄) = Σx / N
Median = Middle value of an ordered dataset
Mode = Most frequently occurring data point

Standard Deviation (σ) = √[ Σ(x - x̄)² / N ]"""
            },
            {
                "title": "Practical Mathematics & Financial Literacy",
                "author": "Seth Kwakye",
                "isbn": "9789988140064",
                "category": "Mathematics",
                "publisher": "Capital Books Ghana",
                "pub_year": 2023,
                "cover_url": "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=400",
                "description": "Simple and compound interest, VAT taxation in Ghana, currency exchange, depreciation, and business math.",
                "content_text": """CHAPTER 2: Simple & Compound Interest in Ghana Cedis (GHS)
Simple Interest (I) = (P × R × T) / 100
where P = Principal Amount, R = Annual Rate (%), T = Time in years.

Compound Interest Formula:
A = P(1 + r/n)^(nt)"""
            },
            {
                "title": "Basic Mathematics & Algebra for West Africa",
                "author": "K. O. Mensah",
                "isbn": "9789988140071",
                "category": "Mathematics",
                "publisher": "Afram Publications",
                "pub_year": 2019,
                "cover_url": "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=400",
                "description": "Foundational arithmetic, fractions, indices, logarithms, linear inequalities, and algebraic substitution.",
                "content_text": """LAWS OF INDICES:
1. xᵃ × xᵇ = xᵃ⁺ᵇ
2. xᵃ ÷ xᵇ = xᵃ⁻ᵇ
3. (xᵃ)ᵇ = xᵃᵇ
4. x⁰ = 1 (for x ≠ 0)
5. x⁻ᵃ = 1 / xᵃ"""
            },

            # --- 3. Popular Science ---
            {
                "title": "WASSCE Integrated Science Core",
                "author": "Dr. E. K. Baidoo",
                "isbn": "9789988123011",
                "category": "Science",
                "publisher": "Asempa Publishers Ghana",
                "pub_year": 2022,
                "cover_url": "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=400",
                "description": "Comprehensive Core Science syllabus preparation for West African Senior School Certificate Examination (WASSCE).",
                "content_text": """CHAPTER 1: Photosynthesis & Plant Physiology
Photosynthesis is the metabolic process by which green plants synthesize glucose from carbon dioxide and water using sunlight energy trapped by chlorophyll.

Chemical Equation:
6CO₂ + 6H₂O + (Sunlight Energy) ➔ C₆H₁₂O₆ + 6O₂

Key Factors Affecting Photosynthesis:
1. Light Intensity
2. Carbon Dioxide Concentration
3. Temperature (Optimal range: 25°C - 35°C)
4. Water Availability

CHAPTER 2: Atomic Structure & Chemical Bonding
An atom consists of three subatomic particles:
- Protons (Positive charge, located in nucleus)
- Neutrons (Neutral charge, located in nucleus)
- Electrons (Negative charge, orbiting in shells)"""
            },
            {
                "title": "BECE Integrated Science for JHS 1-3",
                "author": "G. K. Aboagye",
                "isbn": "9789988150018",
                "category": "Science",
                "publisher": "Unimax Publishers Ghana",
                "pub_year": 2021,
                "cover_url": "https://images.unsplash.com/photo-1507668077129-56e32842fceb?w=400",
                "description": "Full NaCCA aligned JHS Integrated Science coursebook covering Life Sciences, Matter, Energy, and Agriculture.",
                "content_text": """UNIT 1: Diversity of Living & Non-Living Things
Living organisms exhibit seven basic characteristics (MR NIGER D):
1. Movement
2. Respiration
3. Sensitivity / Nutrition
4. Irritability
5. Growth
6. Excretion
7. Reproduction / Death"""
            },
            {
                "title": "SHS Physics for West African Schools",
                "author": "P. N. Okeke & M. W. Anyakoha",
                "isbn": "9789988150025",
                "category": "Science",
                "publisher": "African First Publishers",
                "pub_year": 2020,
                "cover_url": "https://images.unsplash.com/photo-1636466497217-26a8cbeaf0aa?w=400",
                "description": "Newton's laws of motion, electricity, magnetism, optics, wave motion, and atomic physics for SHS students.",
                "content_text": """CHAPTER 3: Newton's Laws of Motion
1. First Law (Inertia): Every body continues in its state of rest or uniform motion in a straight line unless acted upon by an external force.
2. Second Law: F = m · a (Force = Mass × Acceleration)
3. Third Law: For every action, there is an equal and opposite reaction."""
            },
            {
                "title": "Comprehensive Chemistry for Senior High Schools",
                "author": "Dr. S. K. Agyeman",
                "isbn": "9789988150032",
                "category": "Science",
                "publisher": "Ghana Universities Press",
                "pub_year": 2022,
                "cover_url": "https://images.unsplash.com/photo-1603126857599-f6e157fa2fe6?w=400",
                "description": "Organic chemistry, stoichiometry, electrochemistry, periodicity, and chemical kinetics tailored for WASSCE candidates.",
                "content_text": """CHAPTER 8: Organic Chemistry & Hydrocarbons
Hydrocarbons are organic compounds composed solely of Carbon and Hydrogen atoms.

1. Alkanes (Saturated Hydrocarbons): General formula CₙH₂ₙ₊₂ (e.g. Methane CH₄, Ethane C₂H₆)
2. Alkenes (Unsaturated with C=C double bond): General formula CₙH₂ₙ (e.g. Ethene C₂H₄)
3. Alkynes (Unsaturated with C≡C triple bond): General formula CₙH₂ₙ₋₂"""
            },
            {
                "title": "Biology for West Africa",
                "author": "F. O. C. Ndu",
                "isbn": "9789988150049",
                "category": "Science",
                "publisher": "Longman West Africa",
                "pub_year": 2019,
                "cover_url": "https://images.unsplash.com/photo-1530026405186-ed1f139313f8?w=400",
                "description": "Cell biology, genetics, ecology, human digestive system, circulation, and biodiversity in West African ecosystems.",
                "content_text": """CHAPTER 5: Genetics & Mendelian Inheritance
Gregor Mendel established the laws of inheritance through pea plant experiments:
1. Law of Segregation: Alleles separate during gamete formation.
2. Law of Independent Assortment: Genes for different traits segregate independently during gamete development."""
            },
            {
                "title": "Environmental Science & Climate in Ghana",
                "author": "Prof. Chris Gordon",
                "isbn": "9789988150056",
                "category": "Science",
                "publisher": "University of Ghana Press",
                "pub_year": 2023,
                "cover_url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=400",
                "description": "Coastal erosion in Central Region, deforestation, galamsey water pollution, and sustainable conservation strategies.",
                "content_text": """CHAPTER 2: Coastal Dynamics of the Bight of Benin (Winneba Ecosystem)
The coastal marine ecosystems of Effutu and the Central Region of Ghana face pressing challenges due to rising sea levels, tidal surges, and anthropogenic mangrove clearing."""
            },
            {
                "title": "Basic Agricultural Science for Schools",
                "author": "E. A. Asare",
                "isbn": "9789988150063",
                "category": "Science",
                "publisher": "Afram Publications",
                "pub_year": 2021,
                "cover_url": "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?w=400",
                "description": "Soil science, crop production, poultry farming, cocoa cultivation, and modern agricultural technology in West Africa.",
                "content_text": """CHAPTER 4: Soil Fertility & Crop Rotation
Crop rotation involves growing different types of crops in the same area across sequential seasons to maintain soil nitrogen levels naturally."""
            },
            {
                "title": "Health & Hygiene Science in Tropical Regions",
                "author": "Dr. Matilda Osei",
                "isbn": "9789988150070",
                "category": "Science",
                "publisher": "Ministry of Health Ghana Digest",
                "pub_year": 2022,
                "cover_url": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400",
                "description": "Preventive healthcare, sanitation, malaria vector control, nutrition, and public health education.",
                "content_text": """UNIT 3: Malaria Prevention & Mosquito Vector Control
Malaria is caused by Plasmodium parasites transmitted through the bite of an infected female Anopheles mosquito."""
            },

            # --- 4. English & Languages ---
            {
                "title": "WASSCE English Language & Essay Writing",
                "author": "D. S. Sackey & Mercy Tackie",
                "isbn": "9789988160017",
                "category": "English & Languages",
                "publisher": "Asempa Publishers Ghana",
                "pub_year": 2022,
                "cover_url": "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=400",
                "description": "Comprehensive guide for narrative, argumentative, formal letter writing, summary skills, and lexis & structure.",
                "content_text": """SECTION A: Essay & Letter Writing Principles
1. Formal Letters:
   - Requires Two Addresses (Sender top right, Recipient left).
   - Clear Subject Heading in BOLD CAPITALS.
   - Formal Salutation ('Dear Sir/Madam,') and Sign-off ('Yours faithfully,').

2. Argumentative Essays:
   - State your stance clearly in the introduction.
   - Present at least 3 strong points with empirical evidence.
   - Address counter-arguments gracefully before concluding."""
            },
            {
                "title": "BECE English Grammar & Composition",
                "author": "E. V. Asihene",
                "isbn": "9789988160024",
                "category": "English & Languages",
                "publisher": "Unimax Publishers",
                "pub_year": 2021,
                "cover_url": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400",
                "description": "Parts of speech, sentence building, punctuation, idiomatic expressions, and comprehension techniques for JHS.",
                "content_text": """CHAPTER 3: Subject-Verb Agreement (Concord)
Rule 1: A singular subject takes a singular verb; a plural subject takes a plural verb.
Example: 'The librarian reads every morning.' vs 'The librarians read every morning.'

Rule 2: When two singular subjects are connected by 'and', use a plural verb.
Example: 'Kofi and Ama are visiting Winneba library today.'"""
            },
            {
                "title": "Fante & Twi Language Companion",
                "author": "Kwesi Eduafin",
                "isbn": "9789988160031",
                "category": "English & Languages",
                "publisher": "Bureau of Ghana Languages",
                "pub_year": 2020,
                "cover_url": "https://images.unsplash.com/photo-1476275466078-4007374efbbe?w=400",
                "description": "Orthography, grammar, proverbs, and vocabulary of Fante and Twi languages spoken across Central and Ashanti regions.",
                "content_text": """LESSON 1: Basic Greetings & Expressions in Fante
1. Akwaaba = Welcome
2. Mema wo akye = Good morning
3. Mema wo aha = Good afternoon
4. Mema wo ewimbir = Good evening
5. Wo ho te dɛn? = How are you?
6. Me ho yɛ = I am fine."""
            },
            {
                "title": "Creative Writing & African Prose",
                "author": "Prof. Kofi Awoonor",
                "isbn": "9789988160048",
                "category": "English & Languages",
                "publisher": "Ghana Universities Press",
                "pub_year": 1998,
                "cover_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400",
                "description": "Techniques for developing vivid characters, imagery, dialogue, and plot structure inspired by African oral traditions.",
                "content_text": """CHAPTER 2: The Rhythm of African Dialogue
Dialogue in African literature carries the cadence of proverbs, metaphors, and local idioms translated gracefully into English."""
            },
            {
                "title": "Oral Literature & Proverbs of the Effutu People",
                "author": "Neenyi Ghartey VIII",
                "isbn": "9789988160055",
                "category": "English & Languages",
                "publisher": "Winneba Cultural Trust",
                "pub_year": 2018,
                "cover_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400",
                "description": "Documentation of Effutu oral traditions, proverbs, festival chants, and linguistic heritage of Winneba.",
                "content_text": """COLLECTION 1: Effutu Coastal Proverbs
Proverb 1: 'The ocean does not refuse water from a small stream.'
Meaning: Every contribution, no matter how humble, is welcomed by the community."""
            },
            {
                "title": "Comprehension & Summary Guide for West Africa",
                "author": "Mercy Tackie",
                "isbn": "9789988160062",
                "category": "English & Languages",
                "publisher": "Afram Publications",
                "pub_year": 2022,
                "cover_url": "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=400",
                "description": "Answering passage questions accurately, avoiding mindless lifting, and mastering 5-sentence summaries.",
                "content_text": """STRATEGY: Summary Writing Without Mindless Lifting
1. Identify the main thesis of each paragraph.
2. Paraphrase key ideas using your own words.
3. Express each required point in a complete, grammatically sound sentence."""
            },
            {
                "title": "Phonetics & English Pronunciation for Students",
                "author": "Dr. Florence Dolphyne",
                "isbn": "9789988160079",
                "category": "English & Languages",
                "publisher": "Ghana Universities Press",
                "pub_year": 2017,
                "cover_url": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=400",
                "description": "Phonetic symbols, vowel sounds, consonant contrasts, stress patterns, and intonation for clear communication.",
                "content_text": """CHAPTER 1: International Phonetic Alphabet (IPA) Vowels
Understanding pure vowels (/i:/, /ɪ/, /e/, /æ/, /ɑ:/, /ɒ/, /ɔ:/, /ʊ/, /u:/, /ʌ/, /3:/, /ə/) and diphthongs."""
            },
            {
                "title": "African Literature & Poetry Anthology",
                "author": "Kofi Anyidoho",
                "isbn": "9789988160086",
                "category": "English & Languages",
                "publisher": "Woeli Publishing Services",
                "pub_year": 2021,
                "cover_url": "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400",
                "description": "Selected poems and short stories celebrating West African heritage, resilience, and contemporary voices.",
                "content_text": """POEM: Songs of Harvest
We sing of the yam harvest under the full moon,
Where drums reverberate across the Winneba plains,
And elders pour libation to the ancestral soil."""
            },

            # --- 5. Social Studies & History ---
            {
                "title": "Social Studies for Senior High Schools",
                "author": "A. K. Asamoah",
                "isbn": "9789988170016",
                "category": "Social Studies & History",
                "publisher": "Asempa Publishers Ghana",
                "pub_year": 2022,
                "cover_url": "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=400",
                "description": "Self-identity, adolescent reproductive health, national development, democracy, and environmental preservation in Ghana.",
                "content_text": """SECTION 1: Our Environment & National Development
Environmental degradation in Ghana takes three major forms:
1. Deforestation
2. Illegal Mining (Galamsey)
3. Marine & Coastal Pollution

Role of Youth in National Building:
- Active civic participation
- Upholding law and order
- Entrepreneurship and community service."""
            },
            {
                "title": "History of Winneba & Effutu State",
                "author": "Nana Ghartey VII",
                "isbn": "9789988123035",
                "category": "Social Studies & History",
                "publisher": "Winneba Heritage Trust",
                "pub_year": 2019,
                "cover_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400",
                "description": "Historical documentation of Aboakyer deer-hunting festival, Effutu traditions, and Central Region heritage.",
                "content_text": """CHAPTER 1: Origins of the Effutu People & Aboakyer Festival
The Effutu people migrated from the ancient Western Sudan empire under the leadership of Simpa (from whom Winneba derived its native name, Simpa).

The Aboakyer festival is an annual deer-hunting celebration held in May by the two Asafo companies: Tuafo (No. 1) and Dentsefo (No. 2). The first company to capture a live bushbuck deer with their bare hands presents it to the Paramount Chief (Osimpam Neenyi Ghartey)."""
            },
            {
                "title": "History of Ghana & Gold Coast",
                "author": "Prof. Albert Adu Boahen",
                "isbn": "9789988170023",
                "category": "Social Studies & History",
                "publisher": "Sankofa Publishers Accra",
                "pub_year": 2015,
                "cover_url": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=400",
                "description": "Comprehensive political history from ancient kingdoms, trans-Saharan trade, colonial era, to March 6, 1957 Independence.",
                "content_text": """CHAPTER 10: The Path to Independence (March 6, 1957)
On midnight of March 5, 1957, Osagyefo Dr. Kwame Nkrumah stood at the Old Polo Ground in Accra and proclaimed: 'At long last, Ghana, our beloved country, is free forever!'"""
            },
            {
                "title": "Government & Civic Education in West Africa",
                "author": "J. K. Nsiah",
                "isbn": "9789988170030",
                "category": "Social Studies & History",
                "publisher": "Afram Publications",
                "pub_year": 2021,
                "cover_url": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400",
                "description": "The 1992 Constitution of Ghana, arms of government (Executive, Legislature, Judiciary), and rule of law.",
                "content_text": """CHAPTER 4: The 1992 Fourth Republican Constitution
The Constitution establishes Ghana as a sovereign unitary republic based on democratic principles, separation of powers, and fundamental human rights."""
            },
            {
                "title": "Ghanaian Culture, Chieftaincy & Traditions",
                "author": "Dr. Nana Kobina Nketsia V",
                "isbn": "9789988170047",
                "category": "Social Studies & History",
                "publisher": "Sub-Saharan Publishers",
                "pub_year": 2018,
                "cover_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400",
                "description": "Traditional governance systems, stool symbolism, festivals, customary rites, and chieftaincy in modern Ghana.",
                "content_text": """CHAPTER 2: The Stool & Traditional Authority
In Akan and Effutu traditional systems, the Stool symbolizes the soul and unity of the state. Chiefs act as custodians of land and ancestral heritage."""
            },
            {
                "title": "Geography of Ghana & West Africa",
                "author": "Prof. K. B. Dickson & George Benneh",
                "isbn": "9789988170054",
                "category": "Social Studies & History",
                "publisher": "Longman Ghana",
                "pub_year": 2020,
                "cover_url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=400",
                "description": "Physical landscape, climate zones, Volta Lake, mineral resources, agriculture, and urban settlement patterns.",
                "content_text": """CHAPTER 1: Physical Regions of Ghana
Ghana is divided into four main geographical regions:
1. Coastal Savannah Belt
2. Tropical Rainforest Zone
3. Ashanti Highlands & Kwahu Plateau
4. Northern Savannah & Sahelian Fringe"""
            },
            {
                "title": "African Studies & Pan-African Movement",
                "author": "Kwame Nkrumah",
                "isbn": "9789988170061",
                "category": "Social Studies & History",
                "publisher": "Panaf Books",
                "pub_year": 1963,
                "cover_url": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=400",
                "description": "The vision of African unity, continental integration, economic self-reliance, and neo-colonialism analysis.",
                "content_text": """CHAPTER 1: Africa Must Unite
We must unite now or perish under subtle economic domination. The liberation of Ghana is meaningless unless it is linked up with the total liberation of Africa."""
            },
            {
                "title": "Contemporary Social Issues in Modern Ghana",
                "author": "Prof. Dzodzi Tsikata",
                "isbn": "9789988170078",
                "category": "Social Studies & History",
                "publisher": "University of Ghana Press",
                "pub_year": 2023,
                "cover_url": "https://images.unsplash.com/photo-1474939557374-9542446e5b77?w=400",
                "description": "Gender equality, youth employment, rural-urban migration, digital literacy, and social policy in Ghana.",
                "content_text": """CHAPTER 5: Digital Transformation & Youth Entrepreneurship
Mobile money innovation, tech hubs in Winneba and Accra, and empowering young scholars with digital educational resources."""
            },

            # --- 6. Motivational & Leadership ---
            {
                "title": "Atomic Habits: Tiny Changes, Remarkable Results",
                "author": "James Clear",
                "isbn": "9780735211292",
                "category": "Motivational & Leadership",
                "publisher": "Avery / Penguin Random House",
                "pub_year": 2018,
                "cover_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400",
                "description": "An easy and proven framework for building good habits, breaking bad ones, and mastering tiny behaviors for lifelong success.",
                "content_text": """THE 4 LAWS OF BEHAVIOR CHANGE:
1. Make it Obvious (Cue)
2. Make it Attractive (Craving)
3. Make it Easy (Response)
4. Make it Satisfying (Reward)

THE 1% RULE:
If you get 1 percent better each day for one year, you'll end up thirty-seven times better by the time you're done. Small habits don't add up; they compound!"""
            },
            {
                "title": "Rich Dad Poor Dad: Personal Finance for Youth",
                "author": "Robert T. Kiyosaki",
                "isbn": "9781612680194",
                "category": "Motivational & Leadership",
                "publisher": "Plata Publishing",
                "pub_year": 1997,
                "cover_url": "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=400",
                "description": "What the rich teach their kids about money that the poor and middle class do not! Assets vs liabilities.",
                "content_text": """LESSON 1: The Rich Don't Work for Money; Money Works for Them!
An asset is something that puts money into your pocket.
A liability is something that takes money out of your pocket.

If you want to build wealth, buy assets (investments, stocks, businesses, real estate) and reduce liabilities!"""
            },
            {
                "title": "Mindset: The New Psychology of Success",
                "author": "Carol S. Dweck",
                "isbn": "9780345472328",
                "category": "Motivational & Leadership",
                "publisher": "Random House",
                "pub_year": 2006,
                "cover_url": "https://images.unsplash.com/photo-1507668077129-56e32842fceb?w=400",
                "description": "Differentiating fixed mindset from growth mindset and unlocking human potential in academics, sports, and career.",
                "content_text": """GROWTH VS FIXED MINDSET:
In a fixed mindset, people believe their basic qualities, like intelligence or talent, are fixed traits.
In a growth mindset, people understand that abilities can be developed through dedication, hard work, and learning from failure."""
            },
            {
                "title": "The Power of Positive Thinking",
                "author": "Norman Vincent Peale",
                "isbn": "9780743234801",
                "category": "Motivational & Leadership",
                "publisher": "Fireside Books",
                "pub_year": 1952,
                "cover_url": "https://images.unsplash.com/photo-1516979187457-637abb4f9353?w=400",
                "description": "Faith-based practical guide to overcoming worry, building self-confidence, and achieving emotional peace.",
                "content_text": """RULE 1: Formulate a clear mental picture of yourself succeeding. Hold that picture tenaciously. Never permit it to fade. Your mind will seek to develop that picture into reality!"""
            },
            {
                "title": "Think and Grow Rich for African Entrepreneurs",
                "author": "Napoleon Hill & Dr. Mensa Otabil",
                "isbn": "9781585424337",
                "category": "Motivational & Leadership",
                "publisher": "African Leadership Digest",
                "pub_year": 2021,
                "cover_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400",
                "description": "13 principles of personal achievement, definite purpose, persistence, and financial freedom applied to African emerging markets.",
                "content_text": """PRINCIPLE 1: Definite Major Purpose
Whatever the mind of man can conceive and believe, it can achieve! State your goal clearly, write it down, and review it every morning."""
            },
            {
                "title": "The 7 Habits of Highly Effective People",
                "author": "Stephen R. Covey",
                "isbn": "9780743269513",
                "category": "Motivational & Leadership",
                "publisher": "Simon & Schuster",
                "pub_year": 1989,
                "cover_url": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=400",
                "description": "Personal leadership, proactivity, beginning with the end in mind, prioritizing first things first, and win-win relationships.",
                "content_text": """HABIT 1: Be Proactive
Take responsibility for your life. Reactive people are driven by feelings and environment. Proactive people are driven by values."""
            },
            {
                "title": "Discover Your Purpose & Greatness",
                "author": "Dr. Mensa Otabil",
                "isbn": "9789988180015",
                "category": "Motivational & Leadership",
                "publisher": "Alabaster Books Ghana",
                "pub_year": 2019,
                "cover_url": "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400",
                "description": "Inspiring principles on vision, discipline, personal transformation, and impact in African communities.",
                "content_text": """CHAPTER 3: The Power of Personal Vision
Greatness is not an accident of birth; it is the fruit of disciplined vision, daily effort, and unwavering faith."""
            },
            {
                "title": "Leadership & Excellence in Modern Africa",
                "author": "Dr. Patrick Awuah",
                "isbn": "9789988180022",
                "category": "Motivational & Leadership",
                "publisher": "Ashesi Leadership Press",
                "pub_year": 2022,
                "cover_url": "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=400",
                "description": "Ethical leadership, critical thinking, innovation, and problem-solving strategies for the next generation of African leaders.",
                "content_text": """CHAPTER 1: The Courage to Transform
True leadership is about creating light in places where others see impossibility. It requires ethics, empathy, and intellectual rigor."""
            },

            # --- 7. Magazines & Journals ---
            {
                "title": "Ghana Educational Digest & Teacher Journal (Vol. 12)",
                "author": "Ghana Education Service Media",
                "isbn": "9789988190014",
                "category": "Magazines & Journals",
                "publisher": "Ministry of Education Ghana",
                "pub_year": 2024,
                "cover_url": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=400",
                "description": "Quarterly educational journal featuring new NaCCA curriculum updates, STEM initiatives, and teacher spotlight.",
                "content_text": """FEATURE ARTICLE: Expanding Digital Libraries in Central Region
The Effutu Municipal Library Network has launched its digital softcopy repository, enabling thousands of students to access core textbooks online."""
            },
            {
                "title": "West African Journal of Applied Science & Technology",
                "author": "Ghana Academy of Arts & Sciences",
                "isbn": "9789988190021",
                "category": "Magazines & Journals",
                "publisher": "GAAS Press Accra",
                "pub_year": 2023,
                "cover_url": "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=400",
                "description": "Peer-reviewed research articles on renewable solar energy, biotechnology, agricultural yield, and ICT in Ghana.",
                "content_text": """RESEARCH PAPER: Solar Powered Cold Storage for Coastal Fishermen in Winneba
Authors: Dr. E. K. Mensah & Ing. Abena Osei (UEW Engineering Dept)"""
            },
            {
                "title": "Tech Trends Ghana & African Innovation Magazine",
                "author": "Accra Tech Hub Editorial",
                "isbn": "9789988190038",
                "category": "Magazines & Journals",
                "publisher": "Digital Africa Publishing",
                "pub_year": 2024,
                "cover_url": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=400",
                "description": "Showcasing fintech solutions, AI innovations, mobile money ecosystems, and youth startup stories across West Africa.",
                "content_text": """SPECIAL COVERAGE: AI & EdTech Transforming Ghanaian Classrooms
From virtual reading labs to interactive science portals, Ghanaian youth are leveraging digital apps for self-paced learning."""
            },
            {
                "title": "African Geographic & Wildlife Quarterly",
                "author": "Environment Ghana Conservation Society",
                "isbn": "9789988190045",
                "category": "Magazines & Journals",
                "publisher": "Green Heritage Press",
                "pub_year": 2023,
                "cover_url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=400",
                "description": "Photographic journeys through Kakum National Park, Mole National Reserve, Muni-Pomadze Lagoon Winneba, and bird sanctuaries.",
                "content_text": """PHOTO ESSAY: The Migratory Waterfowl of Muni Lagoon, Winneba
Every year, thousands of migratory terns and waders nest along the RAMSAR wetland of Muni Lagoon in Effutu State."""
            },
            {
                "title": "Ghana Business & Economic Review (2025 Edition)",
                "author": "GIPC Economic Research Desk",
                "isbn": "9789988190052",
                "category": "Magazines & Journals",
                "publisher": "Ghana Investment Promotion Centre",
                "pub_year": 2025,
                "cover_url": "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=400",
                "description": "Macroeconomic forecasts, AfCFTA trade opportunities, agricultural exports, and port infrastructure developments.",
                "content_text": """EXECUTIVE SUMMARY: Trade Expansion Under AfCFTA
Ghana's strategic positioning as the Secretariat host of the African Continental Free Trade Area unlocks intra-African commerce."""
            },
            {
                "title": "Effutu Municipal Cultural & Heritage Magazine",
                "author": "Winneba Cultural Directorate",
                "isbn": "9789988190069",
                "category": "Magazines & Journals",
                "publisher": "Municipal Cultural Desk",
                "pub_year": 2024,
                "cover_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400",
                "description": "Special edition covering Aboakyer festival, Winneba Fancy Dress Masquerade Carnival, brass band music, and traditional arts.",
                "content_text": """CELEBRATION: The New Year Fancy Dress Masquerade Festival
Every January 1st, the five masquerade groups of Winneba—Nobles, Tumus, Texas, Red Cross, and Ghosts—parade in elaborate costumes amidst brass band melodies."""
            }
        ]

        added_count = 0
        for b_dict in books_data:
            existing = db.query(Book).filter(Book.title == b_dict["title"]).first()
            if existing:
                # Update content_text and details
                existing.content_text = b_dict.get("content_text")
                existing.cover_url = b_dict.get("cover_url")
                existing.description = b_dict.get("description")
                existing.category = b_dict.get("category")
                continue

            book = Book(**b_dict)
            db.add(book)
            db.commit()
            db.refresh(book)
            added_count += 1

            # Seed 2 Book Copies for each branch
            for br in branches[:3]:
                from app.services.qr_service import generate_qr_token
                qr_tok = generate_qr_token(book.id, br.id)
                copy = BookCopy(
                    book_id=book.id,
                    branch_id=br.id,
                    copy_code=f"B{book.id}-BR{br.id}-01",
                    qr_token=qr_tok,
                    status="available"
                )
                db.add(copy)

        db.commit()
        total_books = db.query(Book).count()
        print(f"[SEED SUCCESS] Seeded 50+ books! Total Books in Catalog now: {total_books}")

    except Exception as e:
        db.rollback()
        print(f"[SEED ERROR] {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_50_books()
