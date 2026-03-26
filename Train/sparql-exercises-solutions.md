# Lösungen zu den SPARQL-Übungen

Verwendete Prefixe:

```sparql
PREFIX : <http://example.org/kg/>
PREFIX ex: <http://example.org/vocab/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
```

## Leicht

### 1. Gib alle Personen mit Namen aus.
```sparql
SELECT ?person ?name
WHERE {
  ?person a foaf:Person ;
          foaf:name ?name .
}
ORDER BY ?name
```

### 2. Gib alle Städte mit Bevölkerungszahl aus.
```sparql
SELECT ?city ?label ?population
WHERE {
  ?city a ex:City ;
        rdfs:label ?label ;
        ex:population ?population .
  FILTER(LANG(?label) = "en")
}
ORDER BY DESC(?population)
```

### 3. Welche Typen gibt es und wie oft kommen sie vor?
```sparql
SELECT ?type (COUNT(?resource) AS ?count)
WHERE {
  ?resource a ?type .
}
GROUP BY ?type
ORDER BY DESC(?count)
```

### 4. Gib alle Kurse mit Credits aus.
```sparql
SELECT ?course ?label ?credits
WHERE {
  ?course a ex:Course ;
          rdfs:label ?label ;
          ex:credits ?credits .
  FILTER(LANG(?label) = "en")
}
ORDER BY ?label
```

### 5. Finde alle Bücher mit Preis.
```sparql
SELECT ?book ?name ?price
WHERE {
  ?book a ex:Book ;
        foaf:name ?name ;
        ex:price ?price .
}
ORDER BY ?price
```

## Mittel

### 6. Finde alle Studierenden in Berlin.
```sparql
SELECT ?student ?name
WHERE {
  ?student a ex:Student ;
           foaf:name ?name ;
           ex:livesIn :Berlin .
}
ORDER BY ?name
```

### 7. Finde alle Personen mit `foaf:name` oder `rdfs:label`.
```sparql
SELECT ?person ?name
WHERE {
  ?person a foaf:Person .
  { ?person foaf:name ?name . }
  UNION
  { ?person rdfs:label ?name . }
}
ORDER BY ?name
```

### 8. Gib alle Studierenden und optional ihre E-Mail aus.
```sparql
SELECT ?student ?name ?email
WHERE {
  ?student a ex:Student ;
           foaf:name ?name .
  OPTIONAL { ?student ex:email ?email . }
}
ORDER BY ?name
```

### 9. Welche Studierenden belegen `:SPARQL101`?
```sparql
SELECT ?student ?name
WHERE {
  ?student a ex:Student ;
           foaf:name ?name ;
           ex:enrolledIn :SPARQL101 .
}
ORDER BY ?name
```

### 10. Welche Bücher mögen Alice?
```sparql
SELECT ?book ?name
WHERE {
  :Alice ex:likesBook ?book .
  ?book foaf:name ?name .
}
ORDER BY ?name
```

### 11. Gib alle Personen aus, die jemanden kennen.
```sparql
SELECT DISTINCT ?person ?name
WHERE {
  ?person a foaf:Person ;
          foaf:name ?name ;
          foaf:knows ?other .
}
ORDER BY ?name
```

### 12. Gib alle Studierenden mit GPA besser als 2.0 aus.
```sparql
SELECT ?student ?name ?gpa
WHERE {
  ?student a ex:Student ;
           foaf:name ?name ;
           ex:gpa ?gpa .
  FILTER(?gpa < 2.0)
}
ORDER BY ?gpa
```

### 13. Finde alle Ressourcen mit deutschem Label.
```sparql
SELECT ?resource ?label
WHERE {
  ?resource rdfs:label ?label .
  FILTER(LANG(?label) = "de")
}
ORDER BY ?label
```

### 14. Gib alle Filme mit Rating größer als 7.5 aus.
```sparql
SELECT ?movie ?name ?rating
WHERE {
  ?movie a ex:Movie ;
         foaf:name ?name ;
         ex:rating ?rating .
  FILTER(?rating > 7.5)
}
ORDER BY DESC(?rating)
```

### 15. Welche Projekte sind aktiv oder geplant?
```sparql
SELECT ?project ?label ?status
WHERE {
  ?project a ex:Project ;
           rdfs:label ?label ;
           ex:status ?status .
  FILTER(?status = "active" || ?status = "planned")
  FILTER(LANG(?label) = "en")
}
ORDER BY ?status ?label
```

## Fortgeschritten

### 16. Zähle, wie viele Studierende pro Stadt wohnen.
```sparql
SELECT ?cityLabel (COUNT(?student) AS ?count)
WHERE {
  ?student a ex:Student ;
           ex:livesIn ?city .
  ?city rdfs:label ?cityLabel .
  FILTER(LANG(?cityLabel) = "en")
}
GROUP BY ?cityLabel
ORDER BY DESC(?count)
```

### 17. Zähle, wie viele Personen an jedem Event teilnehmen.
```sparql
SELECT ?eventLabel (COUNT(?person) AS ?count)
WHERE {
  ?person ex:attends ?event .
  ?event rdfs:label ?eventLabel .
  FILTER(LANG(?eventLabel) = "en")
}
GROUP BY ?eventLabel
ORDER BY DESC(?count)
```

### 18. Finde Studierende, die sowohl Python als auch SPARQL als Skill haben.
```sparql
SELECT ?student ?name
WHERE {
  ?student a ex:Student ;
           foaf:name ?name ;
           ex:hasSkill "Python" ;
           ex:hasSkill "SPARQL" .
}
ORDER BY ?name
```

### 19. Gib alle Personen aus, die ein Praktikum oder einen Nebenjob haben.
```sparql
SELECT ?person ?name
WHERE {
  ?person a foaf:Person ;
          foaf:name ?name .
  { ?person ex:internsAt ?company . }
  UNION
  { ?person ex:worksPartTimeAt ?company . }
}
ORDER BY ?name
```

### 20. Welche Professoren beraten welches Projekt?
```sparql
SELECT ?profName ?projectLabel
WHERE {
  ?prof a ex:Professor ;
        foaf:name ?profName ;
        ex:advisorOf ?project .
  ?project rdfs:label ?projectLabel .
  FILTER(LANG(?projectLabel) = "en")
}
ORDER BY ?profName
```

### 21. Finde alle Studierenden, die Bücher zum Thema SPARQL mögen.
```sparql
SELECT ?student ?name ?bookName
WHERE {
  ?student a ex:Student ;
           foaf:name ?name ;
           ex:likesBook ?book .
  ?book a ex:Book ;
        foaf:name ?bookName ;
        ex:topic "sparql" .
}
ORDER BY ?name
```

### 22. Gib alle Events zwischen 2025-01-01 und 2025-12-31 aus.
```sparql
SELECT ?event ?label ?start ?end
WHERE {
  ?event a ex:Event ;
         rdfs:label ?label ;
         ex:startDate ?start ;
         ex:endDate ?end .
  FILTER(?start >= "2025-01-01"^^xsd:date && ?start <= "2025-12-31"^^xsd:date)
  FILTER(LANG(?label) = "en")
}
ORDER BY ?start
```

### 23. Suche alle Namen, die mit A oder B beginnen.
```sparql
SELECT ?person ?name
WHERE {
  ?person foaf:name ?name .
  FILTER(REGEX(?name, "^(A|B)"))
}
ORDER BY ?name
```

### 24. Welche Studierenden kennen jemanden aus einer anderen Stadt?
```sparql
SELECT DISTINCT ?studentName ?friendName
WHERE {
  ?student a ex:Student ;
           foaf:name ?studentName ;
           ex:livesIn ?city1 ;
           foaf:knows ?friend .
  ?friend foaf:name ?friendName ;
          ex:livesIn ?city2 .
  FILTER(?city1 != ?city2)
}
ORDER BY ?studentName ?friendName
```

### 25. Zähle pro Universität, wie viele Kurse dort unterrichtet werden.
```sparql
SELECT ?uniName (COUNT(?course) AS ?count)
WHERE {
  ?course a ex:Course ;
          ex:taughtAt ?uni .
  ?uni foaf:name ?uniName .
}
GROUP BY ?uniName
ORDER BY DESC(?count)
```

## Bonus

### 26. Gib pro Studierendem die Anzahl der belegten Kurse aus.
```sparql
SELECT ?name (COUNT(?course) AS ?courseCount)
WHERE {
  ?student a ex:Student ;
           foaf:name ?name ;
           ex:enrolledIn ?course .
}
GROUP BY ?name
ORDER BY DESC(?courseCount) ?name
```

### 27. Finde alle Studierenden, die denselben Film mögen wie Alice.
```sparql
SELECT DISTINCT ?student ?name
WHERE {
  :Alice ex:likesMovie ?movie .
  ?student a ex:Student ;
           foaf:name ?name ;
           ex:likesMovie ?movie .
  FILTER(?student != :Alice)
}
ORDER BY ?name
```

### 28. Gib die durchschnittliche GPA pro Universität aus.
```sparql
SELECT ?uniName (AVG(?gpa) AS ?avgGpa)
WHERE {
  ?student a ex:Student ;
           ex:studiesAt ?uni ;
           ex:gpa ?gpa .
  ?uni foaf:name ?uniName .
}
GROUP BY ?uniName
ORDER BY ?avgGpa
```

### 29. Finde alle Ressourcen, die sowohl ein deutsches als auch ein englisches Label haben.
```sparql
SELECT DISTINCT ?resource
WHERE {
  ?resource rdfs:label ?labelDe , ?labelEn .
  FILTER(LANG(?labelDe) = "de")
  FILTER(LANG(?labelEn) = "en")
}
ORDER BY ?resource
```

### 30. Zeige die Top 3 ältesten Personen.
```sparql
SELECT ?person ?name ?age
WHERE {
  ?person a foaf:Person ;
          foaf:name ?name ;
          ex:age ?age .
}
ORDER BY DESC(?age)
LIMIT 3
```
