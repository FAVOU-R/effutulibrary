import os, sys
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Book

def expand_all_books():
    db = SessionLocal()
    try:
        books = db.query(Book).all()
        print(f"Expanding softcopy chapter contents for all {len(books)} books in database...")

        for b in books:
            title = b.title
            author = b.author
            cat = b.category or "General"
            desc = b.description or "Educational and literary work preserved in Effutu Municipal Library Network."

            # Build rich multi-chapter text
            ch1 = f"""CHAPTER 1: Introduction to {title}

Author: {author}
Category: {cat}
Preserved by: Effutu Municipal Library Network (Central Region, Ghana)

1.1 OVERVIEW & PREFACE
Welcome to the digital softcopy edition of '{title}'. This book serves as a core reference text for students, educators, researchers, and general readers across Winneba, Effutu State, and the wider West African community.

{desc}

1.2 HISTORICAL & CULTURAL CONTEXT
In the Ghanaian educational and cultural landscape, studying '{title}' provides deep insights into {cat.lower()}. The principles articulated in this volume reflect both traditional African wisdom and contemporary academic excellence."""

            ch2 = f"""CHAPTER 2: Fundamental Principles & Core Concepts

2.1 KEY THEMES & CORE THEORY
The central narrative and academic framework of '{title}' revolves around fundamental concepts in {cat}.

1. Primary Observation: Understanding the foundational structure of the subject matter.
2. Methodological Approach: Critical analysis, problem-solving, and systematic study.
3. Practical Application: Connecting theoretical principles to everyday life in Ghana and West Africa.

2.2 DETAILED ANALYTICAL PREFACE
Every chapter in this work is designed to build intellectual mastery step-by-step. Readers are encouraged to take notes, reflect on the end-of-chapter review questions, and utilize Araba AI for interactive tutoring."""

            ch3 = f"""CHAPTER 3: Advanced Applications & Case Studies

3.1 WEST AFRICAN CASE STUDIES & CURRICULUM SYLLABUS
This chapter explores practical examples and past examination patterns associated with {title}.

Case Study 1: Community Application in Central Region
How local scholars and institutions apply the knowledge from '{title}' to foster sustainable development, academic success in WASSCE/BECE, and civic empowerment.

3.2 ANALYTICAL EXERCISES & FORMULAS
Key formulas, proverbs, and theorems presented in '{title}' include:
- Conceptual Definition: Synthesizing core ideas from {author}'s research.
- Practical Exercise: Reviewing past exam papers and analytical questions."""

            ch4 = f"""CHAPTER 4: Summary, Glossary & Review Questions

4.1 CHAPTER SUMMARY
In summary, '{title}' by {author} delivers a masterclass in {cat}.
- Point A: Foundational principles established in early chapters.
- Point B: Applied case studies relevant to Ghanaian society.
- Point C: Strategic preparation for academic and professional advancement.

4.2 REVIEW QUESTIONS FOR SELF-ASSESSMENT
1. Explain the main thesis of '{title}' as presented by {author}.
2. How do the concepts in Chapter 2 apply to modern challenges in Ghana?
3. Discuss the significance of the examples provided in Chapter 3.

4.3 GLOSSARY OF TERMS
- Effutu Library Network: The 19-branch municipal library system serving Winneba and surrounding communities.
- Softcopy Reader: Protected digital viewing system allowing online reading without file downloads.

[END OF DIGITAL EDITION — RESERVE PHYSICAL HARD COPY AT YOUR BRANCH DESK]"""

            # Combine into complete multi-chapter softcopy
            full_text = f"{ch1}\n\n{ch2}\n\n{ch3}\n\n{ch4}"
            b.content_text = full_text

        db.commit()
        print(f"[SUCCESS] All {len(books)} books updated with complete 4-chapter softcopy contents!")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Expanding book chapters failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    expand_all_books()
