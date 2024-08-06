from orig_index.overly_simple_embedding import l2_distance, SimpleModel


def test_basic_embedding_functionality():
    # num_vectors=4 is too small, and while hundreds would be more real-world,
    # the test passes with 5.  /shrug
    m = SimpleModel(5)
    emb = m.encode(
        [
            "x = 1",
            "x = 1 + 1",
            "1 + 1 + 2",
            "print('hello world')",
        ]
    )
    assert l2_distance(emb[0], emb[1]) < l2_distance(emb[0], emb[3])
    assert l2_distance(emb[1], emb[2]) < l2_distance(emb[0], emb[3])
