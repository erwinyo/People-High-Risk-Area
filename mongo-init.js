function getTimestamp() {
    return new Date();  // UTC
}

db = db.getSiblingDB("synapsis");   // match MONGO_INITDB_DATABASE
db.createCollection("areas");
db.createCollection("counts");
db.createCollection("people");

db.areas.insertMany([
    {
        "location": "kepatihan",
        "area_name": "depan_gerbang_masuk",
        "polygon_zone": [[735, 721], [1389, 682], [1757, 804], [891, 902]],
        "updated_at": getTimestamp()
    },
    {
        "location": "beringharjo",
        "area_name": "penyeberangan_pasar",
        "polygon_zone": [[1123, 729], [1914, 930], [1910, 1073], [361, 1073]],
        "updated_at": getTimestamp()
    },
    {
        "location": "nolkm",
        "area_name": "area_1",
        "polygon_zone": [[926, 455], [1290, 414], [1402, 985], [1219, 977], [808, 573]],
        "updated_at": getTimestamp()
    },
    {
        "location": "nolkm",
        "area_name": "area_2",
        "polygon_zone": [[1062, 1059], [784, 711], [194, 625], [-1, 756], [3, 1061]],
        "updated_at": getTimestamp()
    },
    {
        "location": "dewi_sartika",
        "area_name": "area_1",
        "polygon_zone": [[1038, 290], [1916, 660], [1910, 894], [934, 327]],
        "updated_at": getTimestamp()
    },
    {
        "location": "dewi_sartika",
        "area_name": "area_2",
        "polygon_zone": [[674, 420], [979, 1069], [546, 1073], [544, 416]],
        "updated_at": getTimestamp()
    },
    {
        "location": "pedati_arah_gudang",
        "area_name": "lorong_gudang",
        "polygon_zone": [[195, 572], [433, 164], [501, 164], [521, 573]],
        "updated_at": getTimestamp()
    },
    {
        "location": "pedati_surken",
        "area_name": "lorong_pasar",
        "polygon_zone": [[337, 166], [534, 576], [121, 572], [278, 164]],
        "updated_at": getTimestamp()
    }
]);
