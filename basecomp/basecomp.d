// Aylwyn Scally 2013
import std.stdio;
import std.path;
import std.getopt;
import std.array;
//import std.format;
//import std.regex;
//import std.conv;
import std.ascii;
import std.string;
import std.algorithm;
//import tango.io.Console;
//import tango.io.FileConduit;
//import tango.io.Stdout;
//import tango.io.stream.TypedStream;
//import tango.text.Util;
//import tango.util.ArgParser;
//import Int = tango.text.convert.Integer;

bool lengthonly = false;

void usage(string cname){
	writefln("usage: %s [-t] [-l | L] [-f] < foo.fa", cname);
}

void main (string[] args)
{
//	char[] name;
	string name;
//	char[] fname;
	int seq = -1;
	long pos = 0;
	int nseqs = 0;
	long tlen = 0;
	int[256] count, tcount;
	bool totalonly = false;
	bool fullnames = false;
	bool seqcount = true;

	try{
		getopt(args, std.getopt.config.caseSensitive,
		"totalonly|t", &totalonly,
		"lengthonly|t", &lengthonly,
		"seqcount|c", &seqcount,
		"fullnames|f", &fullnames);
	} catch (Exception e){
		usage(baseName(args[0]));
		return;
	}

//	char c;
//	foreach (c; stdin.byChunk(char.sizeof)){
//	while (!stdin.eof) {
//		readf(
	foreach (c; LockingTextReader(stdin)){

		if (c == '>'){
			if (seq > 0){
				if (!totalonly)
					printcont(name, pos, count);
				tlen += pos;
				foreach (ic, val; count)
					tcount[ic] += val;
			}
			name.length = 0;
			seq = 0;
			count[] = 0;
		} else if (seq == 0){
			if (c == '\n'){
				seq = 1;
				pos = 0;
				nseqs++;
				if (!fullnames)
					name = split(name)[0];
			} else
				name ~= c;
		} else if (seq > 0 && !isWhite(c)){
			pos++;
			count[c]++;
		}
	}
	if (seq > 0){
		if (!totalonly)
			printcont(name, pos, count);
		tlen += pos;
		foreach (ic, val; count)
			tcount[ic] += val;
	}
//	char[10] outbuf;
	if (seqcount && nseqs > 1 || totalonly){
		auto nseqname = format("%d_sequences", nseqs);
//		nseqname ~= "_sequences";
		printcont(nseqname, tlen, tcount);
	}
}

//void printcont(char[] name, long len, int[256] count){
void printcont(string name, long len, int[256] count){
	writefln("%s\t%d", name, len);
	if (!lengthonly)
		foreach (ic, val; count)
			if (val > 0)
				writefln("%s:\t%d\t%.2f%%", cast(char)ic, val, 100*(cast(float)val) / len);
}
