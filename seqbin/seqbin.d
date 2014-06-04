// Aylwyn Scally 2012
import std.stdio;
import std.path;
import std.getopt;
import std.array;
//import std.format;
import std.conv;
//import std.ascii;
import std.string;
//import std.algorithm;

void usage(string cname){
	writefln("usage:\n%s [[-C chr_col] -p pos_col | -t] [-c count1_col[,count2_col ...]] [-m mean1_col[,mean2_col ...]] [-b binsize | -B binfile | -n binlines] [-H] < chr_file\n\t-t: count total; -H: print headers", cname);
}

class DataBin{ // bin size variable
	string chr;
	long start = 0;
	long[] count;
	float[] meancount;
	long linesread;

	this (long ncount, long nmeans){
		count = new long[](ncount); // change to double to sum non-int values
		meancount = new float[](nmeans); // change to double to average non-int values
		count[] = 0;
		meancount[] = 0;
	}

	void output(long pos, bool nopos){
		static string[] vals;

		if (linesread > 0){
			if (nopos)
				vals = [to!string(linesread)];
			else{
				if (chr)
					vals = [chr];
				else
					vals = [];
				vals ~= [to!string(start), to!string(pos), to!string((start + pos) / 2), to!string(linesread)];
			}
			foreach (e; count)
				vals ~= to!string(e);
			foreach (e; meancount)
				vals ~= to!string(e / linesread);
			writeln(std.array.join(vals, "\t"));
		}
		start = pos;
		linesread = 0;
		count[] = 0;
		meancount[] = 0;
	}
}

class FileBin{ // read bins from file
	File binf;
	string chr;
	long[2] pos;
	long[] count;
	float[] meancount;
	long linesread;

	this (string fname, long ncount, long nmeans){
		binf = File(fname, "r");
		count = new long[](ncount); // change to double to sum non-int values
		meancount = new float[](nmeans); // change to double to average non-int values
		count[] = 0;
		meancount[] = 0;
	}

	bool readbin(){
		static char[] line;
		static char[][] tok;

		if (binf.readln(line) == 0)
			return false;
		tok = split(line);
//		writeln(tok);
		chr = to!string(tok[0]);
		pos[0] = to!long(tok[1]);
		pos[1] = to!long(tok[2]);
		return true;
	}

	bool dataproc(string datachr, long datapos, char[][] countdat, char[][] meandat){
		//TODO check chr == datachr
		if (datapos < pos[0])
			return true;
		while (datapos > pos[1]){
			output();
			if (!readbin())
				return false;
		}
//		writeln(pos[0], " ", datapos, " ", pos[1]);
		if (datapos > pos[0]){
			linesread++;
			foreach (i, x; countdat)
				count[i] += to!int(x);
			foreach (i, x; meandat)
				meancount[i] += to!float(x);
		}
		return true;
	}

	void output(){
		static string[] vals;

		vals = [chr, to!string(pos[0]), to!string(pos[1]), to!string((pos[0] + pos[1]) / 2), to!string(linesread)];
		foreach (e; count)
			vals ~= to!string(e);
		foreach (e; meancount)
			vals ~= to!string(e / linesread);
		writeln(std.array.join(vals, "\t"));
		linesread = 0;
		count[] = 0;
		meancount[] = 0;
	}
}

void main(string[] args) {
	int binsize = 10000;
	int binlines = 0;
	string binfile = "";
	bool dummy;
	bool total = false;
	bool printheaders = false;
//	string colstr = "1,2,3";
	int poscol = 1;
	int chrcol = 0;
	string countcolstr = "";
	string meancolstr = "";

	void opthandler(string opt){
		if (opt == "nocpg")
			dummy = true;
	}
	try{
		getopt(args, std.getopt.config.caseSensitive,
			"binsize|b", &binsize,
			"binfile|B", &binfile,
			"binlines|n", &binlines,
			"printheaders|H", &printheaders,
			"total|t", &total,
			"nocpg", &opthandler,
			"chrcol|C", &chrcol,
			"poscol|p", &poscol,
			"countcols|c", &countcolstr,
			"meancols|m", &meancolstr);
	}
	catch(Exception e){
		usage(baseName(args[0]));
		return;
	}

//	int[] cols;
//	foreach (x;  split(colstr, ","))
//		cols ~= to!int(x) - 1;
//	int[] countcols = cols[2 .. $];
	chrcol--;
	poscol--;
	int[] countcols;
	foreach (x;  split(countcolstr, ","))
		countcols ~= to!int(x) - 1;
	int[] meancols;
	foreach (x;  split(meancolstr, ","))
		meancols ~= to!int(x) - 1;

//	writeln(cols); writeln(meancols);
	string chr;
	char[][] tok;
	long pos = 1;
	if (binfile.length > 0){
		auto bin = new FileBin(binfile, countcols.length, meancols.length);
		auto countdat = new char[][](countcols.length);
		auto meandat = new char[][](meancols.length);
		bin.readbin(); //TODO check if none
		foreach (line; stdin.byLine()){
			if (line.startsWith("#")){
				if (printheaders)
					writeln(line);
				continue;
			}
			tok = split(line);
			if (chrcol >= 0)
				chr = to!string(tok[chrcol]);
			pos = to!long(tok[poscol]);
			foreach (i, x; countcols)
				countdat[i] = tok[x];
			foreach (i, x; meancols)
				meandat[i] = tok[x];
//			writeln(tok);
			if (!bin.dataproc(chr, pos, countdat, meandat))
				break;
//			writeln(bin.linesread, " ", bin.count);
		}
		if (bin.linesread > 0)
			bin.output();
		while (bin.readbin())
			bin.output();
	}else{
		long newpos;
		auto bin = new DataBin(countcols.length, meancols.length);
		foreach (line; stdin.byLine()){
			if (line.startsWith("#")){
				if (printheaders)
					writeln(line);
				continue;
			}
			tok = split(line);
//			writeln(tok);
			if (!total){
				if (chrcol >= 0)
					bin.chr = to!string(tok[chrcol]);
				newpos = to!long(tok[poscol]);
				if (bin.start == 0)
					bin.start = newpos;
				if ((binlines > 0 && bin.linesread >= binlines) || (binlines == 0 && newpos - bin.start + 1 > binsize)){
	//				writeln(bin.start, " ", pos, " ", newpos);
					bin.output(pos, total);
					bin.start = newpos;
					//if fixed bins, bin.start += binsize
				}
				pos = newpos;
			}
			bin.linesread++;
			foreach (i, x; countcols){
				bin.count[i] += to!int(tok[x]);
//				write(tok[x], "\t");
			}
			foreach (i, x; meancols)
				bin.meancount[i] += to!float(tok[x]);
//			writeln("");
		}
		bin.output(pos, total);
	}
}
