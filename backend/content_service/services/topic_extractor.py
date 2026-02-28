import re
from app.database import chapters_collection, topics_collection


def normalize_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# Split on probable subheadings OR large paragraph breaks
TOPIC_SPLIT_REGEX = re.compile(
    r'\n{2,}|\n(?=[A-Z][A-Za-z ,\-]{5,}\n)'
)

# Cleaner question detector
QUESTION_REGEX = re.compile(
    r'([A-Z][^?.!]{15,120}\?)'
)


async def build_topics(book_id: str):
    chapters = await chapters_collection.find(
        {"book_id": book_id}
    ).sort("chapter_index", 1).to_list(None)

    for chapter in chapters:
        raw_text = chapter["text"]
        blocks = TOPIC_SPLIT_REGEX.split(raw_text)

        topic_counter = 1  # ✅ FIXED

        for block in blocks:
            clean = block.strip()

            # Hard quality filter
            if len(clean) < 400:
                continue

            normalized = normalize_text(clean)

            # 1️⃣ Try to extract a meaningful question
            questions = QUESTION_REGEX.findall(normalized)

            if questions:
                title = questions[0]
            else:
                # 2️⃣ Fallback: first clean sentence
                sentences = re.split(r'[.!?]', normalized)
                title = sentences[0].strip()

            title = title[:120]

            doc = {
                "book_id": book_id,
                "chapter_index": chapter["chapter_index"],
                "chapter_title": chapter["title"],
                "topic_index": topic_counter,
                "title": title,
                "text": clean
            }

            await topics_collection.insert_one(doc)
            topic_counter += 1
