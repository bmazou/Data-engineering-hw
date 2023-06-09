# from validator import Validator
import care_providers_loader, validator, utils
from rdflib import Graph, BNode, Literal, Namespace, URIRef
from rdflib.namespace import QB, RDF, XSD

SDMX_CONCEPT = Namespace("http://purl.org/linked-data/sdmx/2009/concept#")
SDMX_DIMENSION = Namespace("http://purl.org/linked-data/sdmx/2009/dimension#")
SDMX_MEASURE = Namespace("http://purl.org/linked-data/sdmx/2009/measure#")
DCT = Namespace("http://purl.org/dc/terms/")
NS = Namespace("http://example.org/ns/")
NSR = Namespace("http://example.org/nsr/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
KRAJ = Namespace("http://ruian.linked.opendata.cz/resource/region/")
OKRES = Namespace("http://ruian.linked.opendata.cz/resource/okres/")
OBOR_PECE = Namespace("http://example.org/ns/obor_pece/")


def create_dimensions(collector: Graph, data):
    okres, kraj = utils.create_okres_kraj(collector)
    
    def create_obory_instances():
        obory = [k.split("---")[-1] for k in data.keys()]
        
        obory_pece = NS.obory_pece
        collector.add((obory_pece, RDF.type, SKOS.ConceptScheme))
        collector.add((obory_pece, SKOS.prefLabel, Literal("Obory péče", lang="cs")))
        collector.add((obory_pece, SKOS.prefLabel, Literal("Fields of care", lang="en")))
        
        for obor in obory:
            temp = obor.replace(" ", "_")
            cur_obor = OBOR_PECE[temp]

            collector.add((cur_obor, RDF.type, SKOS.Concept))
            collector.add((cur_obor, SKOS.inScheme, obory_pece))
            collector.add((cur_obor, SKOS.prefLabel, Literal(obor.capitalize(), lang="cs")))
    
    create_obory_instances()

    obor_pece = NS.obor_pece
    collector.add((obor_pece, RDF.type, RDFS.Property))
    collector.add((obor_pece, RDF.type, QB.DimensionProperty))
    collector.add((okres, RDFS.subPropertyOf, SDMX_DIMENSION.occupation))
    collector.add((obor_pece, SKOS.prefLabel, Literal("Obor péče", lang="cs")))
    collector.add((obor_pece, SKOS.prefLabel, Literal("Field of care", lang="en")))
    collector.add((obor_pece, RDFS.range, SKOS.Concept))
    collector.add((okres, QB.concept, SDMX_CONCEPT.occupation))

    return [okres, kraj, obor_pece]

def create_measure(collector: Graph):
    pocet = NS.pocet
    collector.add( ( pocet, RDF.type, RDFS.Property))
    collector.add( ( pocet, RDF.type, QB.MeasureProperty ) )
    collector.add( ( pocet, SKOS.prefLabel, Literal("Počet", lang="cs") ) )
    collector.add( ( pocet, SKOS.prefLabel, Literal("Count", lang="en") ) )
    collector.add( ( pocet, RDFS.range, XSD.integer ) )
    collector.add( ( pocet, RDFS.subPropertyOf, SDMX_MEASURE.obsValue ) )

    return [pocet]

def create_dataset(collector: Graph, structure):
    dataset = NSR.CareProvidersDataCube
    collector.add((dataset, RDF.type, QB.DataSet))
    collector.add((dataset, QB.structure, structure))

    utils.add_metadata(collector, 
                        dataset,
                        "Number of care providers in a given county and region",
                        "Počet poskytovatelů péče v daném okrese a kraji",
                        "Number of care providers",
                        "Počet poskytovatelů péče",
                        "Number of given care providers in each county and region of the Czech republic",
                        "Počet daných poskytovatelů péče v jednotlivých okresech a krajích ČR",
                        "Care providers",
                        "Poskytovatelé péče")

    return dataset


def create_observations(collector: Graph, dataset, data):
    for index, (dimension, count) in enumerate(data.items()):
        g = NSR["observation-" + str(index).zfill(4)]
        create_observation(collector, dataset, g, dimension, count) 


def create_observation(collector: Graph, dataset, g, dimension, count):
    collector.add((g, RDF.type, QB.Observation))
    collector.add((g, QB.dataSet, dataset))
    
    okres, kraj, obor_pece = dimension.split("---")

    obor_pece_iri = OBOR_PECE[obor_pece.replace(" ", "_")]
    collector.add((g, NS.obor_pece, obor_pece_iri))
    
    kraj_iri = KRAJ[kraj]
    okres_iri = OKRES[okres]
    collector.add((g, NS.kraj, URIRef(kraj_iri)))
    collector.add((g, NS.okres, URIRef(okres_iri)))

    collector.add((g, NS.pocet, Literal(count, datatype=XSD.integer)))

def as_data_cube(data):
    g = Graph()
    dimensions = create_dimensions(g, data)
    measures = create_measure(g)
    structure = utils.create_structure(g, dimensions, measures)
    dataset = create_dataset(g, structure)
    create_observations(g, dataset, data)
    utils.bind_namespaces(g)
    g.bind("obor_pece", OBOR_PECE)
    
    return g

def save_data_cube(data_cube, path):
    with open(path, "w", encoding="utf8") as f:
        f.write(data_cube.serialize(format="ttl"))

def main():
    data = care_providers_loader.load_data("data/care_providers.csv")
    data_cube = as_data_cube(data)
    utils.save_data_cube(data_cube, "output/care_providers.ttl")
    
    validator.check_integrity(data_cube)

if __name__ == "__main__":
    main()