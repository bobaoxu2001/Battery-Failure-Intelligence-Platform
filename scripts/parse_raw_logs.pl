#!/usr/bin/env perl
#
# parse_raw_logs.pl - parse synthetic raw battery cycler telemetry into CSV.
#
# Input format (one record per line):
#   <iso8601> | STATION=<id> | CELL=<id> | V=<volt> | I=<amp> | T=<degC>
#
# Output CSV columns:
#   cell_id,timestamp,station_id,voltage,current,temperature,malformed,reason
#
# Malformed rows (missing fields / non-numeric values) are kept but flagged so
# downstream QA can quantify telemetry health rather than silently dropping data.
#
# Usage:
#   perl scripts/parse_raw_logs.pl [INPUT_LOG] [OUTPUT_CSV]
#   (defaults: data/raw/raw_battery_test_logs.txt -> data/processed/parsed_raw_logs.csv)

use strict;
use warnings;

my $input  = $ARGV[0] // 'data/raw/raw_battery_test_logs.txt';
my $output = $ARGV[1] // 'data/processed/parsed_raw_logs.csv';

open(my $in, '<', $input)  or die "ERROR: cannot open input '$input': $!\n";
open(my $out, '>', $output) or die "ERROR: cannot open output '$output': $!\n";

print {$out} "cell_id,timestamp,station_id,voltage,current,temperature,malformed,reason\n";

my $total     = 0;
my $malformed = 0;
my $num_re    = qr/^-?\d+(?:\.\d+)?$/;   # optional sign, integer or decimal

while (my $line = <$in>) {
    chomp $line;
    next if $line =~ /^\s*$/;       # skip blank lines
    next if $line =~ /^\s*#/;       # skip comment / header lines
    $total++;

    # Pull each field with a tolerant regex; undef if absent.
    my ($ts)      = $line =~ /^\s*(\S+)\s*\|/;
    my ($station) = $line =~ /STATION=(\S+)/;
    my ($cell)    = $line =~ /CELL=(\S+)/;
    my ($volt)    = $line =~ /V=([^\s|]+)/;
    my ($amp)     = $line =~ /I=([^\s|]+)/;
    my ($temp)    = $line =~ /T=([^\s|]+)/;

    my @reasons;
    push @reasons, 'missing_cell'        unless defined $cell;
    push @reasons, 'missing_timestamp'   unless defined $ts;
    push @reasons, 'missing_station'     unless defined $station;
    push @reasons, 'bad_voltage'         unless defined $volt && $volt =~ $num_re;
    push @reasons, 'bad_current'         unless defined $amp  && $amp  =~ $num_re;
    push @reasons, 'bad_temperature'     unless defined $temp && $temp =~ $num_re;

    my $is_bad = @reasons ? 1 : 0;
    $malformed += $is_bad;

    # Normalise undefined fields to empty strings for clean CSV output.
    my $reason = $is_bad ? join(';', @reasons) : 'ok';
    printf {$out} "%s,%s,%s,%s,%s,%s,%d,%s\n",
        $cell    // '',
        $ts      // '',
        $station // '',
        (defined $volt && $volt =~ $num_re) ? $volt : '',
        (defined $amp  && $amp  =~ $num_re) ? $amp  : '',
        (defined $temp && $temp =~ $num_re) ? $temp : '',
        $is_bad,
        $reason;
}

close($in);
close($out);

my $clean = $total - $malformed;
printf STDERR "[parse_raw_logs] parsed %d rows: %d clean, %d malformed -> %s\n",
    $total, $clean, $malformed, $output;
