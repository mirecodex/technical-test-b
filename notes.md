# refactor main.py by miracle

karna melihat skala aplikasi (test) ini maka saya membuat 4 modul utama yang fokus untuk mengatur handling yang menjadi concern tanpa over engineering.

ini yang saya lakukan dan saya dapatkan dengan refactor ini :

**organize file** jadi sesuai instruksi aplikasi ini dipisah menjadi beberapa bagian yang fokus untuk handle per bagian fokus, `main.py` sebagai web logic, `service.py` untuk business logic, ada `repositories.py` untuk data access, dan saya menambahkan juga beberapa file seperti config.py dan juga terakhir pertimbangan terkait schema, awalnya schema ini disatukan ke dalam main, tapi ada perubahan biar lebih enak dilihat. dan juga saya ijin mengganti ID generation dari len(docs_memory) pakai uuid, sebenarnya ga terlalu dipakai karna ini cuma test, tapi mungkin behaviour ini bisa kita bawa nanti kedepan nya di real project. terkait error handling memang ini sangat penting maka dari itu instead of kita menggunakan print statement, sebaiknya gunakan library yang sudah disediakan python yaitu logging hanya dipoles sedikit saja agar proper.

**tradeoff yang saya consider**

jadi saya memilih mengimplementasi workflow nodes LangGraph sebagai closures dalam constructor `RagWorkfowService` daripada menggunakan instance methods. karna untuk mempertahankan functional programming langgraph tapi teatp menangkap dependencies seperti vector store dan embedding service. jadi trade off nya itu adalah dimana akan mengurangi sedikit testability dari individual nodes, tetapi workflow keseluruhan nya tetap mudah di test walau mocked depedencies, kemudian kode yang dibuat tetap bersih.

**maintainability**

- sesuaikan arsitektur dengan project : jadi saya pakai struktur 4-file agar tidak terlalu ribet dan tanpa folder, karna menurut saya main.py (og) tujuan nya simple, jadi maintain nya lebih gampang mudah dipahami karna setiap file tujuan nya beda beda.

- ini tentang inject via depends, jadi tidak memerlukan database atau embedding service yang real, kita cukup implementasi mock dari interface di `VectorStoreRepository` dan `EmbeddingService`

- biasanya python versi 3.10 keatas bisa membuat readble tanpa mengorbankan type safety, jadi disini saya pakai full type hints disemua tempat, agar ketika development times, IDE autocomplete bisa menangkap bug dan untuk jadi inline documentation.

- paling penting ketika ada yang mau maintain, adalah ketika error message nya itu harus jelas biar debugging time nya ga lama, jadi di api, service, dan repository dipasang input validation untuk mencegah data invalid dari proagate lewat sistem, jadi seperti embedding dimension mismatches, empty text, invalid search limit, semua langsung ditampilan jelas.
