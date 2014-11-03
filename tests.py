from parsr import *
import unittest

class myTestCase(unittest.TestCase):
	@classmethod
	def suite(cls):
		suite = unittest.TestSuite()

		for name in cls.tests:
			suite.addTest(cls(name))

		return suite

class myTestSuite(unittest.TestSuite):
	@classmethod
	def suite(cls):
		return cls()

class tokenTests(myTestCase):
	def setUp(self):
		self.tokA = token("(?P<a>a)")
		self.tokB = token("(?P<b>b)")
		self.grA = grammar.fromSymbol(self.tokA)
		self.grB = grammar.fromSymbol(self.tokB)

	tests = ["parse", "merger", "oneChar", "results"]#, "placeOfError"]

	def parse(self):
		self.assertEqual(self.grA.parse("a"), {"a" : "a"})
		self.assertEqual(self.grB.parse("b"), {"b" : "b"})
		self.assertRaises(SyntaxError, self.grA.parse, "b")
		self.assertRaises(SyntaxError, self.grB.parse, "a")

	def merger(self):
		tokC = token("c", merger = lambda x: "CCC")
		grC = grammar.fromSymbol(tokC) 

		self.assertEqual(grC.parse("c"), "CCC")

	def oneChar(self):
		tokEmpty = token("\s*")
		grEmpty = grammar.fromSymbol(tokEmpty)

		self.assertRaises(ValueError, grEmpty.parse, "a")

	def results(self):
		tokString = token("a")
		grString = grammar.fromSymbol(tokString)
		self.assertEqual(grString.parse("a"), "a")

class chainTests(tokenTests):
	def setUp(self):
		super(chainTests, self).setUp()

		self.tokAA = self.tokA >> self.tokA
		self.tokAB = self.tokA >> self.tokB
		self.grAA = grammar.fromSymbol(self.tokAA)
		self.grAB = grammar.fromSymbol(self.tokAB)

	tests = ["parse", "merger", "context", "doubleChain"]

	def parse(self):
		res = self.grAA.parse("aa")
		self.assertTrue(isinstance(res, list))
		self.assertEqual(len(res), 2)
		self.assertEqual(res, [{"a" : "a"}, {"a" : "a"}])

		res = self.grAB.parse("ab")
		self.assertEqual(res, [{"a" : "a"}, {"b" : "b"}])

		self.assertRaises(SyntaxError, self.grAA.parse, "ab")
		self.assertRaises(SyntaxError, self.grAA.parse, "a")
		self.assertRaises(SyntaxError, self.grAB.parse, "aa")

	def merger(self):
		def merger(res):
			return ("%s" % res[1]["b"], "%s" % res[0]["a"])
			
		self.mergedAB = grammar.fromSymbol(chain([self.tokA, self.tokB], merger = merger))
		
		self.assertEqual(self.mergedAB.parse("ab"), ("b", "a"))

	def context(self):
		self.mergedAB = grammar.fromSymbol(chain([self.tokA, self.tokB], merger = lambda x, foo: foo))

		self.assertEqual(self.mergedAB.parse("ab", { "foo" : "bar"}), "bar")

	def doubleChain(self):
		grAAAB = grammar.fromSymbol(chain([self.tokAA, self.tokAB]))

		self.assertEqual(grAAAB.parse("aaab"), [[{"a":"a"}, {"a":"a"}], [{"a":"a"}, {"b":"b"}]])

class repeatTests(tokenTests):
	def setUp(self):
		super(repeatTests, self).setUp()
		
		self.repeatA = grammar.fromSymbol(repeat(self.tokA))
		self.someB = grammar.fromSymbol(repeat(self.tokB, From = 3, To = 4))
		self.minOneA = grammar.fromSymbol(repeat(self.tokA, From = 1))

	tests = ["parse", "FromTo", "merger", "mergeOnce", "withOptional", "nested"]

	def parse(self):
		res = self.repeatA.parse("aaaaa")
		self.assertTrue(isinstance(res, list))
		self.assertEqual(len(res), 5)
		self.assertEqual(res, [{"a" : "a"}, {"a" : "a"}, {"a" : "a"}, {"a" : "a"}, {"a" : "a"}])

		res = self.someB.parse("bbb")
		self.assertTrue(isinstance(res, list))
		self.assertEqual(len(res), 3)
		self.assertEqual(res, [{"b" : "b"}, {"b" : "b"}, {"b" : "b"}])

		self.assertEqual(self.minOneA.parse("a"), [{"a": "a"}])
	
	def FromTo(self):
		self.assertRaises(SyntaxError, self.someB.parse, "aa")
		self.assertRaises(SyntaxError, self.someB.parse, "bb")
		self.assertRaises(SyntaxError, self.someB.parse, "bbbbb")
		self.assertRaises(SyntaxError, self.minOneA.parse, "")

	def merger(self):
		self.repeatA.startSymbol.merger = lambda x: "REPEAT"
		self.someB.startSymbol.merger = lambda x: "SOME"

		self.assertEqual(self.repeatA.parse("aaaaa"), "REPEAT")
		self.assertEqual(self.someB.parse("bbb"), "SOME")

	def mergeOnce(self):
		self.count = 0

		def countMerges(res):
			self.count += 1
			return res

		self.repeatA.startSymbol.merger = countMerges

		self.repeatA.parse("aaaaaa")
		self.assertEqual(self.count, 1)

	def withOptional(self):
		gr = grammar.fromSymbol(optional(token("b")) >> repeat(token("a"), From = 1))

		self.assertEqual(gr.parse("a"), [[], ["a"]])
		self.assertEqual(gr.parse("aaa"), [[], ["a", "a", "a"]])
		self.assertEqual(gr.parse("baaa"), [["b"], ["a", "a", "a"]])

	def nested(self):
		gr = grammar.fromSymbol(repeat( chain([repeat(token("a"), From = 1), repeat(token("b"), From = 1)]) ))
	
		gr.parse("aaaab")
		gr.parse("aaabbbbbbababbabbab")
		gr.parse("abbbab")



class oneOfTests(tokenTests):
	def setUp(self):
		super(oneOfTests, self).setUp()

		self.oneOf = grammar.fromSymbol(oneOf([self.tokA, self.tokB]))

	tests = ["parse", "merge"]

	def parse(self):
		res = self.oneOf.parse("a")
		self.assertEqual(res, {"a" : "a"})
		res = self.oneOf.parse("b")
		self.assertEqual(res, {"b" : "b"})

		self.assertRaises(SyntaxError, self.oneOf.parse, "c")

	def merge(self):
		def merger(l):
			self.assertTrue(not isinstance(l, list))
			return "foo"

		self.oneOf.startSymbol.merger = merger

		self.assertEqual(self.oneOf.parse("a"), "foo")

class optionalTests(tokenTests):
	def setUp(self):
		super(optionalTests, self).setUp()

		self.optional = grammar.fromSymbol(optional(self.tokA) >> self.tokB)

	tests = ["parse", "atEnd", "withOneOfAtEnd"]

	def parse(self):
		res = self.optional.parse("b")
		self.assertEqual(res, [[], {"b": "b"}])

		res = self.optional.parse("ab")
		self.assertEqual(res, [[{"a" : "a"}], {"b" : "b"}])

		self.assertRaises(SyntaxError, self.optional.parse, "cb")

	def atEnd(self):
		gr = grammar.fromSymbol(self.tokA >> optional(self.tokB))

		self.assertEqual(gr.parse("a"), [{"a":"a"}, []])
		self.assertEqual(gr.parse("ab"), [{"a": "a"}, [{"b":"b"}]])
	
	def withOneOfAtEnd(self):
		gr = grammar.fromSymbol(oneOf([self.tokA, self.tokB]) >> optional(self.tokB))

		self.assertEqual(gr.parse("a"), [{"a":"a"}, []])
		self.assertEqual(gr.parse("ab"), [{"a": "a"}, [{"b":"b"}]])
		self.assertEqual(gr.parse("bb"), [{"b": "b"}, [{"b":"b"}]])

class omitTests(tokenTests):
	def setUp(self):
		super(omitTests, self).setUp()

		ls = lexerState([self.tokA], token("\s+"))

		self.withOmitted = grammar.fromSymbol(repeat(self.tokA), lexerStates = [ls])

	tests = ["parse"]
	
	def parse(self):
		res = self.withOmitted.parse("aa a a")
		self.assertEqual(len(res), 4)
		self.assertEqual(res, [{"a": "a"}, {"a" : "a"}, {"a" : "a"}, {"a" : "a"}])


class stateTests(myTestCase):
	tests = ["parse"]

	def parse(self):
		t1 = token("a")
		t2 = token("b")
		t3 = token("c")
		t4 = token("/b")#, popState = True)
		
		aState = lexerState([t1, t2, t3, t4])
		bState = lexerState([t1, t2, t3, t4], omit = token("[ ]+"), pushOn = t2, popOn = t4)

		t = grammar.fromSymbol(repeat(oneOf([t1, t2, t3, t4]), From = 1), lexerStates = [aState, bState])

		self.assertEqual(t.parse("a"), ["a"])
		self.assertEqual(t.parse("b"), ["b"])
		self.assertEqual(t.parse("c"), ["c"])
		self.assertEqual(t.parse("/b"), ["/b"])

		self.assertEqual(t.parse("abc/b"), ["a", "b", "c", "/b"])
		self.assertEqual(t.parse("ab   c /ba"), ["a", "b", "c", "/b", "a"])

		self.assertRaises(SyntaxError, t.parse, "a b c /ba")
		self.assertRaises(SyntaxError, t.parse, "ab c /b a")
		


class grammarTests(myTestCase):
	class lang(grammar):
		whiteSpace = token("[ ]+")
		
		commentEnd = token("[*]/") #, popState
		commentBody = token("([^*/]|([*](?![/]))|((?<![*])[/]))")

		commentStart = token( "/[*]")

		commentState = lexState( [
								"commentEnd"
							], [
								"commentBody"
							],
							pushOn = "commentStart",
							popOn = "commentEnd")

		comment = symbol("commentStart commentEnd")

		oneNumber = token("\d")

		lexerStartState = lexState( [
								"commentStart",
								"oneNumber",
								"minus",
								"plus",
								"mulOperator",
							], [
								"whiteSpace"
							] )
		
		@token("-")
		def minus(res):
			return "SUB"


		@symbol("?minus {1,}*oneNumber")
		def number(res):
			res = flatten(res)
			if res[0] != "SUB":
				numbers = "".join(res[0])
				return int(numbers)

			numbers = "".join(res[1])
			return -1*int(numbers)

		@token("([*](?![/]))|([/](?![*]))")
		def mulOperator(res):
			if res == "*":
				return "MUL"

			return "DIV"

		plus = token("[+]")

		@symbol("plus | minus")
		def addOperator(res):
			if res[0] != "SUB":
				return "ADD"
			return "SUB"

		@symbol("number mulOperator number")
		def mulOperation(res):
			if res[1] == "MUL":
				return res[0] * res[2]
	
			return res[0] / res[2]

		@symbol("number addOperator number")
		def addOperation(res):
			if res[1] == "ADD":
				return res[0] + res[2]
	
			return res[0] - res[2]

		@symbol("mulOperation | addOperation ?comment")
		def expr(res):
			return res[0]


		@symbol("expr")
		def startSymbol(res):
			return res[0]

	def setUp(self):
		pass

	tests = ["createParser", "testParser", "testComment"]

	def createParser(self):
		self.parser = self.lang()

	def testParser(self):
		self.createParser()
		self.assertEqual(self.parser.parse("1 + 2"), 3)
		self.assertEqual(self.parser.parse("1+2"), 3)
		self.assertEqual(self.parser.parse("   1  +2   "), 3)
		self.assertEqual(self.parser.parse("1 - 2"), -1)
		self.assertEqual(self.parser.parse("1-2"), -1)
		self.assertEqual(self.parser.parse("   1  -2   "), -1)
		self.assertEqual(self.parser.parse("1 * 2"), 2)
		self.assertEqual(self.parser.parse("1*-2"), -2)
		self.assertEqual(self.parser.parse("4 / -2"), -2)
		self.assertEqual(self.parser.parse("4/2"), 2)

	def testComment(self):
		self.createParser()
		self.assertEqual(self.parser.parse("1 + 2 /* foobar */"), 3)

class generalTests(myTestCase):
	tests = ["infiniteExpansion"]

	def infiniteExpansion(self):
		a = repeat(definedLater("b"))
		b = repeat(a)
		a.define("b", b)

		gr = grammar.fromSymbol(a)

		self.assertRaises(InfiniteStateExpansion, gr.parse, "")

class parsrTests(myTestSuite):
	def __init__(self, *args, **kwargs):
		super(parsrTests, self).__init__(*args, **kwargs)

		self.addTests(tokenTests.suite())
		self.addTests(chainTests.suite())
		self.addTests(repeatTests.suite())
		self.addTests(optionalTests.suite())
		self.addTests(oneOfTests.suite())
		self.addTests(omitTests.suite())
		self.addTests(stateTests.suite())
		self.addTests(grammarTests.suite())
		self.addTests(generalTests.suite())
	

if __name__ == "__main__":
	unittest.TextTestRunner(verbosity = 2).run(parsrTests.suite())
