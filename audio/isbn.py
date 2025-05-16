from isbnlib import meta, to_isbn13, is_isbn10, is_isbn13, cover

from isbnlib.registry import bibformatters


SERVICE = "openl"

# now you can use the service
isbn = "9787505722460"
print(is_isbn10(isbn))
print(is_isbn13(isbn))
bibtex = bibformatters["bibtex"]
print(bibtex(meta(isbn, SERVICE)))

# convert isbn 10 to isbn 13
isbn13 = to_isbn13(isbn)
print(isbn13)

cover_urls = cover(isbn)
print(cover_urls)
