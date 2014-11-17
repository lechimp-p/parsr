# Parsr

**A tool for creating parsers for self defined languages.**

With this module you can define a grammar for a language, 
instantiate parsers from that grammar and parse bits of 
text according to the grammar.

It was build to make it easy to define grammars for a DSL with
python integration. It is neither fast, nor do i recommend to
use it in production.

Instead you could use it for a quick and dirty exploration of
the design space of a language you just thought about. The parsers
build from your spec run as non deterministic parsers, that is
they could give you any result that could be parsed according to
your grammar. In verbose mode, the parsers give you a detailed 
output of what they are doing. 

The grammars are defined via decorators in a class. There are
two types of objects involved, tokens and symbols. A token matches
some strings, a symbol is a more complex structure build from
other tokens and symbols.

In the first stage of the parsing, the text is broken up into
distinct pieces (no non-determinism here!) according to the tokens
in you grammar. In the second stage, the parser tries to group the
tokens according to the symbols in every possible way.

In your grammar class you can define what happens, if a token or
symbol is found. You can attach a function to that token/symbol,
that could process the found string or the results of a subsymbol
to generate other objects or intermediate data as result.

The parsers (currently ?) do not support fixity (that would make 
it possible to parse 1 + 1 * 2 as 1 + (1 * 2)), so you might 
be forced to use parantheses more often than you would like to. 
You could work around this behaviour by constructing a intermediate
syntax tree.

**Disclaimer**: As i'm no computer scientist, forgive me if i use
some terminology inappropriately. I'm also aware, that building
parsers already is explored for some times and there are well known
and battle proven algorithms and strategies to implement parsers.
So this is just my personal naive approach.

## Technical documentation 

A complete example could be found in example.py. 

To define a grammar create a class deriving from the grammar base 
class.

```
class myGrammar(grammar):
```

In the class body you can define tokens by either instantiatiating
a token directly or using a decorator-version for that instantiated
token.

```
a = token("a")
bc = token("[bc]")
```

A token is the base of any grammar. It is defined by a python
regexp (which is "a" for token a and "b|c" for token bc). In the
first phase of the parsing, the text is "lexed". That means it is
broken into tokens according to the given regexps. For that reason,
you need to always give regexps that match at least one char. The 
parsing itself later acts on the stream of tokens yielded that 
way.

The lexer always is in a state, from which you have defined at 
least one, called lexerStartState

```
lexerStartState = lexState([ "a", "b"], ["whitespace"])
```

A lexState is initialised with two lists, one containing the tokens 
to insert into the stream, and the second containing tokens that 
should be ommited during the lexing process.
The names of the tokens (as all names you see later) always need to 
be given as strings. On instantiation, the grammar will fill them 
with the according objects.
The lexer starts at the front of the text. Then it first tries the 
tokens in the second (omit) list in the order they appear in the 
list. If the start of the text matches, it just skips over the 
matched part and goes on from the start. If no omit token matches, 
the lexer preceeds with the list of tokens in the given order. If it
finds one of that tokens, it inserts that token	into the stream of 
tokens and goes on after the matched part of the text. If it can't 
find one of the tokens, it raises a LexerError.

You could use multiple states for the lexing, by defining new 
lexerStates:

```
commentState = lexState(["commentEnd"], ["commentBody"],
                        pushOn = "commentStart", popOn = "commentEnd")
```

Like that you could define a state to omit everything between a 
comment start and end sign. The pushOn argument to lexState defines 
a token, after which the state should be used as lexer state. popOn 
defines a token, after whose appearance the state should get dropped. 
The state will only ever get dropped, if the popOn tokens appears in 
the list of tokens or the omit list. The pushOn-token, the other way 
round, needs to be matched in another state, if the state should ever 
get to be used.

The tokens can be combined to more complex symbols:

```
bcThenA = symbol("bc a")
```

You can use the following syntax in the call to symbol:

 syntax   | semantics                                             
----------|---------------------------------------------------------
 a b c    | Match the symbols or tokens a, b and c one after another 
 (a b c)  | Match the symbols or tokens a, b and c one after another 
 a|b|c    | Match one of a, b or c.                               
 ?a       | Match a or not.                                       
 \*a      | Match any number of appearances of a                  
 {x,}\*a  | Match at least x appeareances of a.                   
 {,x}\*a  | Match at most x appeareances of a.                    
 {x,y}\*a | Match between x and y appeareances of a.                   

Like the tokens in the states of the lexer, the names in the symbols 
defined	that way will be replaced by the real symbols on instantiation 
of the grammar. You have to define one symbol called startSymbol, that 
is the point where the parsing of the text will start.
The parsing of the defined grammar works as multi state parsing. This 
means, the parser contains multiple possible pathes through the grammar. 
It eliminates possibilities by pushing the token one after another and 
testing the current	states against the pushed token. After pushing a 
token, it expands the leftover possibilities until a possibility looking 
for a new token is reached.
It is of course easily possible to create a symbol that expands to 
infinity, like:

```
a = symbol("*b")
b = symbol("*a")
```

This case is indicated by throwing an InfiniteStateExpansion error.

There are three more errors that could possibly be thrown when parsing
a text. The first is StatesExhausted. This error indicates, that the 
parser went out of states, which happens when the text currently parsed 
doesn't match the defined grammar.

NotCompleted indicates, that the text so far indeed matches the grammar,
but that the startSymbol of the grammar was not completed.

AmbigiousResults indicates that the text fits the grammar, but can't be
parsed clearly to one interpretation. Using the symbol a|a for example
would lead to such a grammar, because the parser can't decide which of
the two options to take. You can get rid of such errors by looking into
the definition of grammars closely to find the place where the two 
options arise. You could also catch the exception and inspect on the 
current state to go get the different possibilities.

By instantiating your grammar with the argument verbose=True, you get
an output of the parsing process, which might help you to find the
place where things go wrong. It could also give you an idea of how the 
parsing works.
