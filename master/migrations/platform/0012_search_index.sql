-- DAT-10: one full-text index for chats, artifacts, files and code. Text is normalised for Turkish in
-- Python before it is stored or queried (see search_index.py), so the plain unicode61 tokenizer is enough.
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    title, body,
    kind UNINDEXED, owner_id UNINDEXED, ref UNINDEXED,
    tokenize = 'unicode61 remove_diacritics 2'
);
