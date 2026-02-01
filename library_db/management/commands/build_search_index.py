
import re
from django.core.management.base import BaseCommand
from django.core.cache import cache
from library_db.models import Book
import pickle # We need this to store the Trie object in the cache

# --- NEW: Trie Data Structure Implementation ---
class TrieNode:
    def __init__(self):
        self.children = {}
        self.book_ids = set() # Store book IDs at the end of each word

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word, book_id):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.book_ids.add(book_id)

    def search_prefix(self, prefix):
        node = self.root
        for char in prefix:
            if char not in node.children:
                return set() # Prefix not found
            node = node.children[char]
        
        # If prefix is found, collect all book IDs from this node and its children
        return self._collect_all_ids_from_node(node)

    def _collect_all_ids_from_node(self, node):
        ids = set(node.book_ids)
        for child_node in node.children.values():
            ids.update(self._collect_all_ids_from_node(child_node))
        return ids

class Command(BaseCommand):
    help = 'Builds and caches the Inverted Index and the Trie for book searching.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO('Building search indexes...'))
        
        # --- Build Inverted Index (for full word search) ---
        inverted_index = {}
        books = Book.objects.all()
        for book in books:
            content = f"{book.title} {book.description or ''}"
            words = set(re.findall(r'\w+', content.lower()))
            for word in words:
                if word not in inverted_index:
                    inverted_index[word] = set()
                inverted_index[word].add(book.pk)
        
        cache.set('book_inverted_index', inverted_index, timeout=None)
        self.stdout.write(self.style.SUCCESS('Inverted Index built and cached.'))

        # --- Build Trie (for prefix search on titles) ---
        trie = Trie()
        for book in books:
            # We only index titles for the live prefix search
            title_words = set(re.findall(r'\w+', book.title.lower()))
            for word in title_words:
                trie.insert(word, book.pk)
        
        # Pickle the Trie object before caching it
        pickled_trie = pickle.dumps(trie)
        cache.set('book_trie_index', pickled_trie, timeout=None)
        self.stdout.write(self.style.SUCCESS('Trie index for titles built and cached.'))