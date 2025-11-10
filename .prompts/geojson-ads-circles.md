{{template("new-tool.md", tool_name="geojson-ads-circles")}}

We get some CSV data for ad POIs from our advertising partner, the format is:

```csv
Name,Address,Postcode,lat,lng
Boots,"11-19 Lower Parliament Street, Nottingham",NG1 3QS,52.9555186000,-1.1465924000
Boots,"1 Devonshire Walk, Derby",DE1 2AH,52.9200880000,-1.4733948000
Boots,"MSU10 Level 2, Birmingham",B5 4BE,52.4775185000,-1.8959484000
Boots,"42-43 High Street, Grantham",NG31 6NE,52.9109703000,-0.6418423000
Boots,"34-40 Cheapside, Barnsley",S70 1RT,53.5515802000,-1.4792972000
...
```

The tool can be run like this:

```
geojson-ads-circles <input-file> <keyword> <radius> <output-file>
```

E.g.

```
geojson-ads-circles input-file.csv my-keyword 3000 output.geojson
```

And it will produce output.geojson with the circles encoded, for example:


```
{
    "type": "FeatureCollection",
    "name": "my-keyword",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [-1.1465924, 52.9555186]
            },
            "properties": {
                "subType": "Circle",
                "radius": 3000,
                "Name": "Boots",
                "Address": "11-19 Lower Parliament Street, Nottingham, NG1 3QS",
                "lat": 52.9555186,
                "lng": -1.1465924
            }
        },
        ...
    ]
}

Note that the postcode field may not be present in the input file. If it is, the postcode of each POI is added to the address.
