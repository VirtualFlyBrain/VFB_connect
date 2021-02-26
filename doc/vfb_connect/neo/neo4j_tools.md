Module vfb_connect.neo.neo4j_tools
==================================

Functions
---------

    
`chunks(l, n)`
:   Yield successive n-sized chunks from l.

    
`cli_credentials()`
:   Parses command line credentials for Neo4J rest connection;
    Optionally specify additional args as a list of dicts with
    args required by argparse.add_argument().  Order in list
    specified arg order

    
`cli_neofj_connect()`
:   

    
`dict_cursor(results)`
:   Takes JSON results from a neo4J query and turns them into a list of dicts.

    
`escape_string(strng)`
:   

Classes
-------

`Neo4jConnect(endpoint='http://pdb.virtualflybrain.org', usr='neo4j', pwd='vfb')`
:   Thin layer over REST API to hold connection details, 
    handle multi-statement POST queries, return results and report errors.

    ### Descendants

    * vfb_connect.neo.query_wrapper.QueryWrapper

    ### Methods

    `commit_csv(self, url, statement, chunk_size=1000, sep=',')`
    :

    `commit_list(self, statements, return_graphs=False)`
    :   Commit a list of statements to neo4J DB via REST API.
        Prints requests status and warnings if any problems with commit.
            - statements = list of cypher statements as strings
            - return_graphs, optionally specify graphs to be returned in JSON results.
        Errors prompt warnings, not exceptions, and cause return  = FALSE.
        Returns results list of results or False if any errors are encountered.

    `commit_list_in_chunks(self, statements, verbose=False, chunk_length=1000)`
    :   Commit a list of statements to neo4J DB via REST API, split into chunks.
        cypher_statments = list of cypher statements as strings
        base_uri = base URL for neo4J DB
        Default chunk size = 1000 statements. This can be overridden by KWARG chunk_length.
        Returns a list of results. Output is indistinguishable from output of commit_list (i.e. 
        chunking is not reflected in results list).

    `get_lookup(self, limit_by_prefix=None, include_individuals=False, limit_properties_by_prefix=('RO', 'BFO', 'VFBext'))`
    :   Generate a name:ID lookup from a VFB neo4j DB, optionally restricted by a list of prefixes
        limit_by_prefix -  Optional list of id prefixes for limiting lookup.
        credentials - default = production DB
        include_individuals: If true, individuals included in lookup.

    `list_all_edge_props(self)`
    :

    `list_all_node_props(self)`
    :

    `rest_return_check(self, response)`
    :   Checks status response to post. Prints warnings to STDERR if not OK.
        If OK, checks for errors in response. Prints any present as warnings to STDERR.
        Returns True STATUS OK and no errors, otherwise returns False.

    `test_connection(self)`
    :