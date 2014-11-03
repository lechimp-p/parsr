"""
	Name: Parsr
	Version: 1.0.0
	Author: Richard Klees
	Contact: richard.klees@rwth-aachen.de
	License: MIT

	A tool for creating parsers for self defined languages.
"""

import re
import pdb
import os.path as path

class ParsrError(Exception):
	"""
		General exception class for errors from the parsr module.
	"""
	pass

class LexerError(ValueError, SyntaxError, ParsrError):
	"""
		Indicates a failure during lexing of the input.

		Has attributes text, which is the parsed text,
		pos, which is the position in the text where the
		error occured, and lexerState, which is the state
		of the lexer when the error occured.
	"""
	def __init__(self, text, pos, lexerState):
		self.text = text
		self.pos = pos
		self.lexerState = lexerState

	def __str__(self):
		if len(self.text) - self.pos > 10:
			t = self.text[self.pos:(self.pos + 10)]
		else:
			t = self.text[self.pos:]

		t = t.replace("\n", "\\n")
		
		tokens = self.lexerState.tokens + self.lexerState.omit

		toks = "%s or %s" % (", ".join(i.name for i in tokens[:-1]), tokens[-1].name)

		lines = self.text.count("\n", 0, self.pos)
		pos = self.pos - self.text.rfind("\n", 0, self.pos) 

		return "At line %d, position %d ('%s'): Expected %s." % (lines, pos, t, toks)

class StatesExhausted(SyntaxError, ParsrError):
	"""
		Indicates that the parsr ran out of possible 
		interpretations of the text.

		Has attribute state, which is the state who threw
		the exception and expectedTokens which is the list
		of tokens that were expected to be found before
		states exhausted.
		
		Also carries text and position in the text where
		the error occured.

	"""
	def __init__(self, state, expectedTokens = None):
		self.state = state
		self.expectedTokens = expectedTokens

	def __str__(self):
		return 


class NotCompleted(SyntaxError, ParsrError):
	def __init__(self, state):
		self.state = state

	def __str__(self):
		return "Symbol not completed."

class AmbigiousResults(SyntaxError, ParsrError):
	def __init__(self, state):
		self.state = state
			
	def __str__(self):
		return "Ambigious results."

class InfiniteStateExpansion(RuntimeError, ParsrError):
	def __init__(self, state):
		self.state = state

	def __str__(self):
		return "States expand to infinity."

class grammar(object):
	"""
		Base class for grammar.
	"""
	@classmethod
	def fromSymbol(cls, symbol, verbose = False, lexerStates = None):
		if not lexerStates:
			lexerStates = [lexerState(symbol.getTokens(), [])]
		return grammar(lexerStates, symbol, verbose = verbose)

	def __init__(self, lexerStates = None, startSymbol = None, lexerStartState = None, verbose = False):
		self.lexerStates = None

		if not lexerStates and not startSymbol and not lexerStartState:
			self.initSymbols()
			self.initLexerStates()
		else:
			self.lexerStates = lexerStates

			if lexerStartState:
				self.lexerStartState = lexerStartState

			self.startSymbol = startSymbol

		if not self.lexerStates:
			raise TypeError("No lexer states.")

		if not self.startSymbol:
			raise TypeError("No start symbol.")

		if not hasattr(self, "lexerStartState") or not self.lexerStartState:
			self.lexerStartState = self.lexerStates[0]


		self.verbose = verbose

	def parse(self, text, context = None):
		"""
			Try to match this grammar to a text.

			context : dict - This dict could be used to pass some context
						     dependend variables to the mergers of the symbols.
		"""
		if context is None:
			context = {}

		tokens = self.lex(text)

		state = None

		try:
			state = parserRootState(self.startSymbol, verbose = self.verbose)

			if self.verbose:
				print "\n== Start parsing. == \n"

			for t in tokens:
				if self.verbose:
					print "\n\n\n--> Push result from token %s at position %d: %s" % (t.token.name, tokens.index(t) + 1, t.result)
				state.pushToken(t)
		except RuntimeError as e:
			if ("%s" % e)[:5] == "maxim":
				raise InfiniteStateExpansion(state)
			raise


		return state.result(context)

	def lex(self, text):
		"""
			Turn text to a list of token matches.
		"""
		if self.verbose:
			print "\n == Start lexing. == \n"

		tokStream = []

		states = [self.lexerStartState]

		pushOn = {}

		for state in self.lexerStates:
			if state.pushOn:
				if isinstance(state.pushOn, list):
					for p in state.pushOn:
						pushOn[p] = state
				else:
					pushOn[state.pushOn] = state

		pos = 0

		while pos < len(text):
			if len(states) == 0:
				states = [self.lexerState]
			
			if self.verbose:
				print "\nRemaining Text starts at: '%s'" % self.adjustCodeOutput(text[pos:])

			# Check weather next chars should be omitted
			omitted = False

			for tok in states[-1].omit:
				if self.verbose:
					print "Omit: %s" % tok.name

				match = tok.match(text, pos)

				if match:
					if states[-1].popOn == tok:
						states.pop()
						if self.verbose:
							print "Popped state, new state is %s" % states[-1].name
					if tok in pushOn:
						states.append(pushOn[tok])
						if self.verbose:
							print "Pushed state, new state is %s" % states[-1].name

					omitted = True
					pos = match.end
					break

			if omitted:
				continue

			# Next character mus be some token.
			success = False

			for tok in states[-1].tokens:
				if self.verbose:
					print "Checking: %s" % tok.name

				match = tok.match(text, pos)

				if match:
					if states[-1].popOn == tok:
						states.pop()
						if self.verbose:
							print "Popped state, new state is %s" % states[-1].name
					if tok in pushOn:
						states.append(pushOn[tok])
						if self.verbose:
							print "Pushed state, new state is %s" % states[-1].name

					if self.verbose:
						print "-----> Found from position %d to %d: %s" % (match.start, match.end, match.result)

					tokStream.append(match)

					success = True
					pos = match.end
					break

			if success:
				continue

			# That surely is a problem...
			raise LexerError(text, pos, states[-1])

		if self.verbose:
			print "\n"
			print "---> %d tokens found." % len(tokStream)
			print "\n"

		return tokStream

	def adjustCodeOutput(self, text):
		newLinePos = text.find("\n")
		if newLinePos == -1:
			return text

		if text[:newLinePos].strip() == "":
			return "\\n" + self.adjustCodeOutput(text[(newLinePos+1):])

		return text[:newLinePos]

	def initLexerStates(self):
		self.lexerStates = []

		for key, item in ((i, getattr(self, i)) for i in dir(self)):
			if not isinstance(item, lexState):
				continue

			omit = []

			def getToken(name):
				if not name in self.definedSymbols:
					raise ValueError("Token %s not defined." % name)
				t = self.definedSymbols[name]
				if not isinstance(t, token):
					raise ValueError("%s is no token." % name)
				return t 

			for o in item.omit:
				omit.append(getToken(o))

			tokens = []

			for n in item.tokens:
				tokens.append(getToken(n))

			if item.pushOn:
				if isinstance(item.pushOn, str):
					pushOn = [getToken(item.pushOn)]
				else:
					pushOn = [getToken(p) for p in item.pushOn]
			else:
				pushOn = None

			if item.popOn:
				popOn = getToken(item.popOn)
			else:
				popOn = None

			l = lexerState(tokens, omit, pushOn, popOn)
			l.name = key
			self.lexerStates.append(l)

			if key == "lexerStartState":
				self.lexerStartState = l 

		if not hasattr(self, "lexerStartState"):
			raise TypeError("No lexerStartState defined.")
			

	def initSymbols(self):
		self.definedSymbols = {}

		for key, item in ((i, getattr(self, i)) for i in dir(self)):
			if not isinstance(item, symbol):
				continue

			item = item.__copy__()
			item.name = key

			if key == "startSymbol":
				self.startSymbol = item

			self.definedSymbols[key] = item

			for key2, item2 in self.definedSymbols.viewitems():
				item2.define(key, item)
				item.define(key2, item2)


class lexerState(object):
	def __init__(self, tokens, omit = None, pushOn = None, popOn = None):
		if omit is None:
			omit = []
		elif not isinstance(omit, list):
			omit = [omit]

		self.omit = omit

		self.tokens = []
		
		for t in tokens:
			if isinstance(t, token):
				self.tokens.append(t)
			elif isinstance(t, lexerState):
				self.tokens.extend(t.tokens)
			else:
				raise TypeError("lexerState: can only contain other tokens, not '%s'" % type(t))

		#self.tokens.sort(key = lambda x: x.preference, reverse = True)

		self.pushOn = pushOn
		self.popOn = popOn

		self.name = "lexerState"

class lexState(object):
	"""
		Lexer state for deferred creation of a real lexer state.
	"""
	def __init__(self, tokens, omit = None, pushOn = None, popOn = None):
		if omit is None:
			omit = []
		elif not isinstance(omit, list):
			omit = [omit]

		self.omit = omit
		self.tokens = tokens
		self.pushOn = pushOn
		self.popOn = popOn


class metaSymbol(type):
	"""
		Metaclass for enabling the BNF-like syntax for creation of symbols.
	"""
	def __call__(cls, *args, **kwargs):
		if not cls == symbol or len(args) != 1 or len(kwargs) != 0:
			return super(metaSymbol, cls).__call__(*args, **kwargs)

		if isinstance(args[0], basestring):
			return createSymbolFromBNF(args[0])

		sym = super(metaSymbol, cls).__call__(args[0])
		sym.name = args[0]
		return sym


class symbol(object):
	"""
		Base class for any symbol in the grammar.
	"""
	__metaclass__ = metaSymbol

	def __init__(self, merger, name):
		self.merger = merger
		if not name:
			self.name = self.__class__.__name__
		else:
			self.name = name

	def __copy__(self):
		"""
			Get a copy of this symbol.
		"""
		raise NotImplementedError

	def __call__(self, fun):
		"""
			Add fun as merger if symbol has no merger.

			Used for symbols as decorators for their mergers.
		"""
		if self.merger:
			raise RuntimeError("Symbol already has a merger.")

		if not callable(fun):
			raise TypeError("Merger for symbol must be callable.")

		self.merger = fun

		return self

	def getState(self, parent = None, verbose = False, indent = 0):
		"""
			Get a stateful representation of this symbol.
		"""
		return self.stateType(self, parent = parent, verbose = verbose, indent = indent)

	def getTokens(self, gottenFrom = None):
		"""
			Get a list of all subTokens.

			Leave 'gottenFrom' empty, it is there for not running 
			into infinit recursion in recursive symbols.

			This just encapsulates that mechanism and then calls
			__getToken__, which should just pass on gottenFrom to
			sub-symbols and return a list of all tokens.
		"""
		if gottenFrom is None:
			gottenFrom = []

		if self in gottenFrom:
			return []

		gottenFrom.append(self)

		return self.__getTokens__(gottenFrom)

	def __getTokens__(self, gottenFrom):
		"""
			Return a list of tokens within this symbol. Pass on
			gottenFrom to calls to getTokens from sub-symbols.
		"""
		raise NotImplementedError

	def define(self, name, symbol, definedIn = None):
		"""
			Define a sub-symbol which is not defined by now.

			Uses a similar mechanism than getTokens to not run
			into infinite recursion.

			Calls __define__ which has to be reimplemented.
		"""
		if definedIn is None:
			definedIn = []

		if self in definedIn:
			return

		definedIn.append(self)

		return self.__define__(name, symbol, definedIn)

	def __define__(self, name, symbol, definedIn):
		"""
			Define an undefined symbol. Pass on defined in
			to calls to define from sub-symbols.
		"""
		raise NotImplementedError

	def __rshift__(self, other):
		"""
			Use as symbol >> symbol to create a chain of two or more
			symbols.
		"""
		return chain([self, other])

class definedLater(symbol):
	def __init__(self, name):
		self.name = name

	def getState(self, *args, **kwargs):
		raise RuntimeError("%s not defined." % self.name)

	def __copy__(self):
		return definedLater(self.name)

	def __define__(self, name, symbol, definedIn):
		return

	def __getTokens__(self, gottenFrom):
		raise NotImplementedError("Undefined symbol: %s" % self.name)

class containsSymbols(symbol):
	def __getTokens__(self, gottenFrom):
		tokens = []

		for r in self.symbols:
			tokens.extend(r.getTokens(gottenFrom))

		return tokens

	def __define__(self, name, symbol, definedIn):
		for r in [i for i in self.symbols]:
			if isinstance(r, definedLater) and r.name == name:
				self.symbols[self.symbols.index(r)] = symbol 
			else:
				r.define(name, symbol, definedIn)


class parserState(object):
	"""
		A state of the parser.

		While parsing, a tree of possible interpretations is build.
		Every node in the tree (the state) can have possible substates,
		that means states that have to be parsed before the node itself
		is found.
		A state can be made valid, that means it does not represent a
		possibility anymore, but a true result of the parsing. The 
		parent has to handle that event, either by spawning new possible
		substates or declaring itself as valid.
	"""
	def __init__(self, symbol, parent = None, verbose = False, indent = 0):
		# The symbol controlling this state.
		self.symbol = symbol

		# The parent state of this state.
		self.parent = parent

		# State can have possible next states to 
		# follow it.
		self._possibilities = [] 

		# Possibilities that should be evaluated
		# with next token
		self._addedPossibilities = []

		# Possibilities that should be removed
		self._removedPossibilities = []

		# State of object, weather it is yielding
		# possibilities atm.
		self._yieldsPossibilities = False

		self.verbose = verbose
		self.indent = indent

	def possibilities(self):
		"""
			Yield possibilities of state.

			Does changes (i.e. inserting new possibilites and removing of
			invalid possibilites) afterwards.
		"""
		self._yieldsPossibilities = True

		for p in self._possibilities:
			if p in self._removedPossibilities:
				continue
			yield p

		for p in self._addedPossibilities:
			self._possibilities.append(p)

		self._addedPossibilities = []

		for p in self._removedPossibilities:
			if p in self._possibilities:
				self._possibilities.remove(p)

		self._removedPossibilities = []

		self._yieldsPossibilities = False 

		if self.isInvalid():
			self.makeInvalid()

	def leafs(self):
		"""
			Yield leafs of the possibility tree.
		"""
		for p in self.possibilities():
			for l in p.leafs():
				yield l

	def isInvalid(self):
		"""
			Let state decide weather it is invalid. 

			Needed for invalidation of self after execution of possibilities.
			
			This implementation returns len(self._possibilities) == 0.
		"""
		return len(self._possibilities) == 0

	def pushToken(self, token):
		"""
			Change parserState according to this token.
		"""
		raise NotImplementedError

	def addPossibility(self, state):
		"""
			Add a possibility to this state. 

			The possibility will be evaluated at next token.
		"""
		if not self._yieldsPossibilities:
			self._possibilities.append(state)
		else:
			self._addedPossibilities.append(state)

	def addPossibilityNow(self, state):
		"""
			Add a possibility to this state.

			The possibility will be evaluated with current token.
		"""
		self._possibilities.append(state)

	def makeValid(self):
		"""
			Tell the parent, that this state ends and is valid.
		"""
		if not self.parent:
			return

		self.parent.setValidPossibility(self)

	def setValidPossibility(self, state):
		"""
			This is called by a child, if it was made valid.
		"""
		raise NotImplementedError

	def makeInvalid(self):
		"""
			Tell the parent that this state is invalid.

			Just call setInvalidPossibility(self) at parent
			if parent is there.
		"""
		if not self.parent:
			raise StatesExhausted(self)

		self.parent.setInvalidPossibility(self)

	def setInvalidPossibility(self, state):
		"""
			Remove a substate of this state.

			A substate is either a possibility or a followUp.
		"""
		self.removePossibility(state)

		if len(self._possibilities) == 0:
			# I there are no possibilities left, this state is
			# impossible as well.
			self.makeInvalid()

	def removePossibility(self, state):
		"""
			Plainly removes state from possibilities without invoking other stuff.
		"""
		if not state in self._possibilities and not state in self._addedPossibilities:
			raise ValueError("State is no substate of me.")

		if self._yieldsPossibilities:
			self._removedPossibilities.append(state)
		else:
			self._possibilities.remove(state)

	def result(self):
		"""
			Return the result of this state.
		"""
		raise NotImplementedError

	def indentation(self):
		"""
			Indentation helper for creating more usefull
			verbose output.
		"""
		return "|   " * self.indent




class parserRootState(parserState):
	"""
		Root state for parsing. 

		Catches results and nows how to push tokens to possibilities. 
	"""
	def __init__(self, symbol, verbose = False):
		super(parserRootState, self).__init__(symbol, verbose = verbose)

		# Will contain all possibilities that were valid
		# after last token was pushed.
		self.validPossibilities = []

		# Will contain a list of tokens that i tried to
		# find at the last pushed token
		self.lastTokens = []
		self.lastPushedToken = None
	
		# Create one possibility for startSymbol.
		self.addPossibility(symbol.getState(parent = self, verbose = verbose))

	def isInvalid(self):
		"""
			Is invalid when no possibilities are left and no valid possibilities
			were found at last parsing.
		"""
		return len(self._possibilities) == 0 and len(self.validPossibilities) == 0

	def pushToken(self, token):
		"""
			Clears validPossibilities and pushes tokens to
			possibilities.
		"""
		self.validPossibilities = []

		if len(self._possibilities) == 0:
			raise StatesExhausted(self, self.lastTokens)

		self.lastTokens = []

		for l in self.leafs():
			self.lastTokens.append(l)

		for p in self.possibilities():
			p.pushToken(token)

	def setValidPossibility(self, state):
		self.validPossibilities.append(state)

		self.removePossibility(state)

	def result(self, context):
		if len(self.validPossibilities) == 0:
			raise NotCompleted(self)

		if len(self.validPossibilities) > 1:
			raise AmbigiousResults(self)

		return self.validPossibilities[0].result(context)



class token(symbol):
	def __init__(self, regexp, merger = None):
		name = "\"" + regexp.replace("\n", "\\n").replace("\t", "\\t") + "\""
		super(token, self).__init__(merger, name = name)
		self.origRegexp = regexp

		try:
			self.regexp = re.compile(regexp)
		except Exception as e:
			raise ValueError("Can't compile python regexp: '%s', %s" % (self.name, e)) 
	def __copy__(self):
		return token(self.origRegexp, self.merger)

	def __getTokens__(self, gottenFrom):
		return [self]

	def __define__(self, name, symbol, definedIn):
		pass

	class matchType(object):
		def __init__(self, token, text, result, start, end):
			self.token = token
			self.result = result 
			self.start = start
			self.end = end
			self.text = text

	def match(self, text, pos):
		res = self.regexp.match(text, pos)

		if not res:
			return 

		if len(res.group(0)) == 0:
			raise ValueError("Don't use tokens that match strings with zero length.")

		matchResult = res.groupdict()
		if len(matchResult) == 0:
			matchResult = res.group(0)

		return self.matchType(self, res.group(0), matchResult, res.start(), res.end())

	class stateType(parserState):
		def __init__(self, *args, **kwargs):
			super(token.stateType, self).__init__(*args, **kwargs)
			self._result = None

			assert self.parent

		def leafs(self):
			yield self

		def pushToken(self, token):
			assert self.parent

			if self.verbose:
				print "%s%s: Checking %s --> %s" % (self.indentation(), self.symbol.name, token.text.replace("\n", "\\n"), "success" if token.token == self.symbol else "fail")

			if token.token == self.symbol:
				self._result = token
				self.makeValid()
			else:
				self.makeInvalid()

			return

		def result(self, context):
			assert self.parent
			assert not self._result is None

			if self.symbol.merger:
				return self.symbol.merger(self._result.result, **context)
			
			return self._result.result


class chain(containsSymbols):
	"""
		A chain of other symbols.
	"""
	def __init__(self, symbols, merger = None, name = None):
		assert len(symbols) > 0
		super(chain, self).__init__(merger, name)
		self.symbols = symbols

		for pos, sym in enumerate(self.symbols):
			if isinstance(sym, basestring):
				self.symbols[pos] = definedLater(sym.strip())

	def __copy__(self):
		return chain([i.__copy__() for i in self.symbols], self.merger, name = self.name)

	class stateType(parserState):
		"""
			The parserState type for the chain.
		"""
		def __init__(self, symbol, parent = None, verbose = False, indent = 0, withInitialPossibility = True):
			super(chain.stateType, self).__init__(symbol, parent = parent, verbose = verbose, indent = indent)

			# Start with -1 because currentPosition
			# gets iterated before it is used.
			self.currentPositions = {} 
			self.results = {}

			# That will be the possibility the chain currently works on.
			self.currentlyWorksOn = None

			if withInitialPossibility:
				initialPossibility = self.symbol.symbols[0].getState(parent = self, verbose = self.verbose, indent = self.indent + 1)
				self.addPossibility(initialPossibility)

			assert self.parent

		def pushToken(self, token):
			if self.verbose:
				print "%sIn %s:" % (self.indentation(), self.symbol.name)
			assert self.currentlyWorksOn is None
			assert self.parent

			for p in self.possibilities():
				assert p in self.currentPositions
				assert p in self.results
				self.currentlyWorksOn = p 
				p.pushToken(token)

			self.currentlyWorksOn = None

		def setValidPossibility(self, state):
			if self.verbose:
				print "%s%s: Valid subsymbol %s at position %d found" % (self.indentation(), self.symbol.name, self.symbol.symbols[self.currentPositions[state]].name, self.currentPositions[state])

			assert state in self.results

			self.results[state].append(state)
			self.currentPositions[state] += 1

			# That means, all subsymbols were found and this state
			# is still there => it's valid!
			if len(self.symbol.symbols) == self.currentPositions[state]:
				newState = self.fork(state)
				newState.makeValid()
				return

			self.createNextState(state)
			self.removePossibility(state)

		def createNextState(self, validState):
			# We have to modify self.currentlyWorksOn for a 
			# moment, because the state we are currently Working on
			# could have add a new state, that is validated directly,
			# so we would be in an incorrect context for adding the
			# next state.
			curWorksOn = self.currentlyWorksOn
			self.currentlyWorksOn = validState
	
			nextState = self.symbol.symbols[self.currentPositions[validState]].getState(parent = self, verbose = self.verbose, indent = self.indent + 1)

			if not validState in self._possibilities or not curWorksOn or self._possibilities.index(validState) <= self._possibilities.index(curWorksOn):
				self.addPossibility(nextState)
			else:
				self.addPossibilityNow(nextState)

			# Set back to original state we was working on
			self.currentlyWorksOn = curWorksOn

		def fork(self, validState):
			"""
				Create a copy without state and add it as possibility to parent.
				Remove all copied states from self.
			"""
			if not self.parent:
				raise RuntimeError("No parent to fork.")

			copy = self.__class__(self.symbol, parent = self.parent, verbose = self.verbose, withInitialPossibility = False)

			copy.results = { validState : self.results[validState]}
			copy.currentPositions = { validState : self.currentPositions[validState]}

			self.removePossibility(validState)

			self.parent.addPossibility(copy)

			if isinstance(self.parent, chain.stateType):
				assert copy in self.parent.currentPositions
				assert copy in self.parent.results


			return copy

		def copyResAndCurPosFor(self, state):
			assert self.parent

			if self.currentlyWorksOn is None:
				self.results[state] = []
				self.currentPositions[state] = 0
				return

			self.results[state] = [i for i in self.results[self.currentlyWorksOn]]
			self.currentPositions[state] = self.currentPositions[self.currentlyWorksOn]

		def addPossibility(self, state):
			assert self.parent

			super(chain.stateType, self).addPossibility(state)
			self.copyResAndCurPosFor(state)

			assert state in self.results
			assert state in self.currentPositions

		def addPossibilityNow(self, state):
			assert self.parent

			super(chain.stateType, self).addPossibilityNow(state)
			self.copyResAndCurPosFor(state)

			assert state in self.results
			assert state in self.currentPositions

		def removePossibility(self, state):
			super(chain.stateType, self).removePossibility(state)

			if state in self.results:
				del self.results[state]
			if state in self.currentPositions:
				del self.currentPositions[state]

		def result(self, context):
			assert self.parent

			posResults = []

			for res in self.results.viewvalues():
				if len(res) == len(self.symbol.symbols):
					posResults.append(res)

			if len(posResults) == 0: 
				raise NotCompleted(self)

			if len(posResults) > 1:
				raise AmbigiousResults(self)

			l = [i.result(context) for i in posResults[0]]

			if self.symbol.merger:
				return self.symbol.merger(l, **context)
			
			return l



class repeat(containsSymbols):
	"""
		A repetition of n to m times a symbol.
	"""
	def __init__(self, symbol, From = 0, To = -1, merger = None, name = None):
		super(repeat, self).__init__(merger, name)

		if isinstance(symbol, basestring):
			symbol = definedLater(symbol.strip())

		self.symbols = [symbol]
		self.From = From
		self.To = To

	def __copy__(self):
		return repeat(self.symbols[0].__copy__(), self.From, self.To, self.merger, name = self.name)

	class stateType(chain.stateType):
		def __init__(self, symbol, parent = None, verbose = False, indent = 0, withEmptyResult = False, *args, **kwargs):
			super(repeat.stateType, self).__init__(symbol, parent = parent, verbose = verbose, indent = indent, *args, **kwargs)

			if withEmptyResult:
				self.results[None] = []
			else:
				self._addEmptyResultToParentEventually()

		def _addEmptyResultToParentEventually(self):
			if len(self.results) == 1 and len(self.results[self.results.keys()[0]]) == 0 and self.symbol.From == 0:
				self.addedEmptyResult = True
				emptyResult = self.__class__(self.symbol, parent = self.parent, verbose = self.verbose, withInitialPossibility = False, withEmptyResult = True)
				self.parent.addPossibility(emptyResult)
				emptyResult.makeValid()

		def setValidPossibility(self, state):
			assert self.parent

			if self.verbose:
				print "%s%s: Valid symbol %s found for the %d'th time." % (self.indentation(), self.symbol.name, self.symbol.symbols[0].name, len(self.results[state]) + 1)

				
			self.results[state].append(state)

			if len(self.results[state]) < self.symbol.To or self.symbol.To == -1:
				self.createNextState(state)

			if len(self.results[state]) >= self.symbol.From:
				newState = self.fork(state)
				newState.makeValid()
			else:
				self.removePossibility(state)

		def result(self, context):
			assert self.parent

			posResults = []

			for res in self.results.viewvalues():
				if len(res) >= self.symbol.From and (len(res) <= self.symbol.To or self.symbol.To == -1):
					posResults.append(res)

			if len(posResults) == 0:
				raise NotCompleted(self)

			# Find longest matching result
			res = posResults[0]
			for r in posResults:
				if len(r) > len(res):
					res = r

			l = [i.result(context) for i in res]

			if self.symbol.merger:
				return self.symbol.merger(l, **context)

			return l
			
class optional(repeat):
	def __init__(self, symbol, merger = None, name = None):
		super(optional, self).__init__(symbol, From = 0, To = 1, merger = merger, name = name)
	def __copy__(self):
		return optional(self.symbols[0].__copy__(), self.merger, name = self.name)


class oneOf(containsSymbols):
	"""
		Match one of the given symbols.
	"""
	def __init__(self, symbols, merger = None, name = None):
		super(oneOf, self).__init__(merger, name)
		self.symbols = symbols

		for pos, sym in enumerate(self.symbols):
			if isinstance(sym, basestring):
				self.symbols[pos] = definedLater(sym.strip())

	def __copy__(self):
		return oneOf([i.__copy__() for i in self.symbols], self.merger, name = self.name)
	
	class stateType(chain.stateType):
		"""
			The parserState for oneOf.
		"""
		def __init__(self, symbol, parent = None, verbose = False, indent = 0, withInitialPossibility = True, *args, **kwargs):
			super(oneOf.stateType, self).__init__(symbol, parent = parent, verbose = verbose, indent = indent, withInitialPossibility = False, *args, **kwargs)

			if withInitialPossibility:
				for sym in self.symbol.symbols:
					poss = sym.getState(parent = self, verbose = self.verbose, indent = self.indent + 1)
					self.addPossibility(poss)

		def setValidPossibility(self, state):
			if self.verbose:
				print "%s%s: Option %s found" % (self.indentation(), self.symbol.name, state.symbol.name)

			self.results[state].append(state)

			newState = self.fork(state)
			newState.makeValid()

			self.removePossibility(state)

		def result(self, context):
			posResults = []

			for res in self.results.viewvalues():
				assert len(res) <= 1
				if len(res) == 1:
					posResults.append(res)

			if len(posResults) == 0:
				raise NotCompleted(self)

			if len(posResults) > 1:
				raise AmbigiousResults(self)

			l = posResults[0][0].result(context)

			if self.symbol.merger:
				return self.symbol.merger(l, **context)
			
			return l


class bnfGrammar(grammar):

	def parse(self, text):
		return super(bnfGrammar, self).parse(text, context = {"parser" : self})

	_empty = token("[ ]+")

	_name = token("\w+")
	_number = token("\d+")
	_leftP = token("[(]")
	_rightP = token("[)]")
	_leftSP = token("[{]")
	_rightSP = token("[}]")
	_delim = token(",")
	_qumark = token("[?]")
	_star = token("[*]")
	_bar = token("[|]")

	lexerStartState = lexState([
						"_number",
						"_name",
						"_leftP",
						"_rightP",
						"_leftSP",
						"_rightSP",
						"_delim", 
						"_qumark",
						"_star",
						"_bar"
					], [
						"_empty"
					])

	@chain( [oneOf(["_chain", "_name"])] )
	def _simpleSymbol(res, parser):
		if isinstance(res[0], str):
			return definedLater(res[0])
	
		return res[0]

	@chain(["_leftSP", optional("_number"), "_delim", optional("_number"), "_rightSP"])
	def _fromToPart(res, parser):
		if len(res[1]) > 0:
			if len(res[3]) > 0:
				return (int(res[1][0]), int(res[3][0]))
			else:
				return (int(res[1][0]), -1)
		else:	
			if len(res[1]) == 0 and len(res[3]) == 0:
				return (0, -1)
			else:
				return (0, int(res[2][0]))

	@chain([optional("_fromToPart"), "_star", " _simpleSymbol"])
	def _repeat(res, parser):
		if len(res[0]) == 0:
			return repeat(res[2])
		
		return repeat(res[2], From = res[0][0][0], To = res[0][0][1])

	@chain(["_qumark", " _simpleSymbol"])
	def _optional(res, parser):
		return optional(res[1])

	_noOneOfSymbol = oneOf(["_repeat", "_optional", "_simpleSymbol"])
	
	@chain([repeat(chain(["_noOneOfSymbol", "_bar"])), "_noOneOfSymbol", "_bar", "_noOneOfSymbol"])
	def _oneOf(res, parser):
		res = flatten(res)

		temp = []

		res.append(",")
		
		while len(res) > 0:
			temp.append(res.pop(0))
			res.pop(0)

		return oneOf(temp)

	
	@chain(["_leftP", repeat("symbol", From = 1), "_rightP"]) 
	def _chain(res, parser):
		res = res[1]

		return chain(res)

	symbol = oneOf(["_repeat", "_optional", "_chain", "_oneOf", "_name"])


	@repeat("symbol", From = 1)
	def startSymbol(res, parser):
		if len(res) == 0:
			return res

		return parser._chain.merger([None, res, None], parser)

_bnfParser = bnfGrammar()

def createSymbolFromBNF(text):
	return _bnfParser.parse(text)


# Utils

def flatten(lists):
	"""
		Flatten nested list to one list.
	"""
	res = []

	for l in lists:
		if isinstance(l, list):
			res.extend(flatten(l))
		else:
			res.append(l)

	return res

def flattenIter(lists):
	"""
		Iterate over the flattened lists.
	"""
	for l in lists:
		if isinstance(l, list):
			for i in flattenIter(l):
				yield i
		else:
			yield l
