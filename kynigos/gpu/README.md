# Κυνηγός Κλειδιών — GPU (WebGPU / secp256k1)

Αναζήτηση Bitcoin Puzzle #71 στη GPU μέσω WebGPU (secp256k1 + hash160 σε WGSL).
100% τοπικά/offline· το κλειδί, αν βρεθεί, δεν φεύγει από τη συσκευή.

- Ανοίγει σε Chrome/Edge (Windows/Mac/Android) και Safari iOS 26+ με WebGPU.
- Συμβατό με τη μορφή προόδου `KYN1:` (Εισαγωγή/Εξαγωγή με αντιγραφή/επικόλληση), μονάδα chunk 65.536.
- Η πρόοδος αποθηκεύεται τοπικά (localStorage) ανά browser/συσκευή.
