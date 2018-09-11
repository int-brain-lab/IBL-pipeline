'''
ibl.ingest

'shadowed' copies of main tables for external data load most classes
here will be defined using <downstream_module>.RealClass.definition;

only if some merging/disambiguation will definitions be augmented/modified
in some way with additional tables to facillitate the difference.
these differences should still result in tables compatbile with data copying
via insert from select (e.g: Foo.insert(Bar.fetch()))

NOTE:

Since downstream modules involve cross-module definitions, those modules
should be imported as 'ds_module' in order to prevent accidental linkages
to downstream tables in the upstream schema.

For example:

  - foo.py defines Foo
  - bar.py defines Bar referencing foo.Foo

  - ingest.bar imports .. foo (for some other reason than foo.Foo)
  - ingest.bar imports .. bar (to get foo.Foo schema string)

In this case, setting ingest.bar.Bar.definition = bar.Bar.definition 
now creates accidental link to downstream foo.Foo table because 'bar' points
to the downstream module. If foo/bar had been imported as ds_foo/ds_bar,
respectively, the table definition syntax would not properly resolve in
the scope of ingest.bar and the definition would fail.

For this reason, it is best to err on the side of caution by importing
`as ds_` to prevent this kind of issue.

'''
