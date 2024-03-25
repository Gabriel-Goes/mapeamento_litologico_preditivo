@startuml
title Preditor Terra

entity Folhas {
    + Código: String
    + Geometria: Polygon
    ----
    - Folhas: List<folhas>
}

entity Dados_Geofísicos{
    + Atributo: Float
    + Geometria: Point
}

@enduml
