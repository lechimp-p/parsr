from parsr import *

# In this example we will parse s-expression with
# simple operators and numbers. An s-expression 
# (in our case) either is a number or has the form
# (op expr1 expr2) where op is an operator (here: +-*/%)
# and expr is another s-expression. (+ 1 1) is an 
# s-expression that encodes 1 + 1.
# The parser will parse expression of said form and show
# the result of the encoded calculations.


# To define our grammar we derive from the grammar-base
# class.
class SExpr(grammar):
    # A grammar is build from tokens and symbols, and
    # i think it is a good idea to define the tokens first.
    # They are atomic. We need tokens for the parantheses,
    # numbers, operators and for space.

    # To define a token, we use the token constructor and
    # give it an ordinary regexp.
    space = token("[ ]+") 

    # These are the parantheses.
    lp = token("[(]")
    rp = token("[)]")

    # We could also use the token constructor as a decorator
    # to invoke some code whenever the token is matched.
    @token("\d+")
    def number(res):
        # Here we like to transform it to an integer, since we
        # later want to make calculations with the numbers.
        # Note, that we already know we could savely call int()
        # since res was matched by the given regexp before.
        return int(res)

    # That's the same for the supported operators.   
    @token("[+-/%\\*]")
    def operator(res):
        # But here we return lambdas to perform the calculations.
        if res == "+":
            return lambda x,y: x + y
        elif res == "-":
            return lambda x,y: x - y
        elif res == "*":
            return lambda x,y: x * y
        elif res == "/":
            return lambda x,y: x/y
        elif res == "%":
            return lambda x,y: x % y
        
        raise TypeError("Unknown operator: '%s'" % res) 
    
    # The lexer always runs in some state, this is the state he starts in.
    # The first parameter (tokens) are the names of the tokens that are matched 
    # in the state. The tokens are matched in their order of appearance here,
    # so make sure you first try a longer the longer token, if you have to
    # tokens starting with the same char (e.g. match ++ before +).
    # The second parameter (omit) defines tokens that will be dropped during 
    # parsing, but still be tried. The tokens in this list will be tried before
    # the tokens in the first list.
    lexerStartState = lexState(["rp", "lp", "number", "operator"], ["space"])

    # You could define more lexerStates here, e.g. to have a special state to 
    # match comments.
    # For these states, you need to use the third (pushOn) and fourth (popOn)
    # parameter. Both expect a name of a token. pushOn controls, when the lexer
    # will switch to your state, that is after he found the token given as 
    # pushOn. You need to make sure, that some other state has that token in its
    # tokens list, since your state would never be used (pushed) if the token 
    # was not found. When the token given as popOn is found, the state 
    # previously used will be used again. So make sure, your state itself 
    # matches said token. 

    # Yay, the first symbol. We use the symbol constructor as decorator
    # since we want to perform some calculation.
    @symbol("lp operator expr expr rp")
    # The matched subsymbols become a list, provided as argument.
    def op_expr(res):
        # This is just for documentational purpose.
        operator = res[1]
        l = res[2]
        r = res[3]
        return operator(l, r) 

    @symbol("op_expr|number")
    def expr(res):
        return res[0]
    
    # The start symbol is the symbol that should match
    # the complete string. Of course we also could have
    # named expr to startSymbol directly, but the symbol
    # for op_expr would have been looking kind of weird
    # then.
    @symbol("expr")
    def startSymbol(res):
        return res[0]

# To get the parser, we instantiate our grammar. If you want to see, what the 
# parser does during parsing, pass it a verbose=True.
parser = SExpr()

# Some example s-expressions.
exmpl1 = "(+ 10 2)"
exmpl2 = "(* 5 (+ (- 7 3) 2))"
exmpl3 = "(% (+ 2 5) 2)"

# And the actual parsing. You could give a context parameter, to define some
# environment for the parsing. The context will be passed to the symbol and
# token functions as second parameter after res.
print parser.parse(exmpl1)
print parser.parse(exmpl2)
print parser.parse(exmpl3)

# So that's it. If you like to play with the grammar, here are some ideas
# what to do:
# * Make it possible to parse multiline s-expressions.
# * Add a power operator. Or some other operator you could think of.
# * Make the parser understand floats.
# * Make it possible to give an arbitrary number of sub-expressions to
#   an operator.
# * Try to switch the parser to infix operators with parantheses.
# * Try to implement comments, e.g. in python or c++ style.
# * Try to find out, what happens, if introduce ambiguities by omitting
#   the parantheses.
