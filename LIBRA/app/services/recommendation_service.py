from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models import Thesis


def _clean_text(value):
    if not value:
        return ""

    return str(value).strip()


def _build_document(thesis):
    """
    Combine the most useful thesis text fields for similarity.
    """

    return " ".join(
        [
            _clean_text(thesis.title),
            _clean_text(thesis.abstract),
            _clean_text(thesis.keywords),
            _clean_text(thesis.research_field),
            _clean_text(thesis.research_topic),
            _clean_text(thesis.research_subtopic),
            _clean_text(thesis.program.program_name if thesis.program else ""),
        ]
    )


def get_related_theses(
    thesis,
    limit=3
):
    """
    Return the most similar theses using TF-IDF + Cosine Similarity.

    Output:
    [
        {
            "thesis": Thesis object,
            "similarity": 92
        }
    ]
    """

    candidate_theses = (
        Thesis.query
        .filter(
            Thesis.id != thesis.id,
            Thesis.is_archived.is_(False)
        )
        .all()
    )

    if not candidate_theses:
        return []

    all_theses = [thesis] + candidate_theses

    documents = [
        _build_document(item)
        for item in all_theses
    ]

    # Avoid failure if every document is empty.
    if not any(document.strip() for document in documents):
        return []

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=12000
    )

    try:
        matrix = vectorizer.fit_transform(
            documents
        )
    except ValueError:
        return []

    similarities = cosine_similarity(
        matrix[0:1],
        matrix[1:]
    ).flatten()

    ranked_indexes = similarities.argsort()[::-1]

    related = []

    for index in ranked_indexes:

        score = similarities[index]

        if score <= 0:
            continue

        related_thesis = candidate_theses[index]

        related.append(
            {
                "thesis": related_thesis,
                "similarity": round(
                    float(score) * 100
                )
            }
        )

        if len(related) >= limit:
            break

    return related