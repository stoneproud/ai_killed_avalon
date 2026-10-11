#!/usr/bin/env perl
use strict;
use warnings;
use JSON::PP;
use File::Temp qw(tempdir);

# Synthetic fixtures only. No keys, game state, network, Git, or publication.
# Exercises the actual p1 -> p3 and p1 -> p2 interfaces, rather than copies.
@ARGV == 3 or die "usage: perl p7_protocol_integration_v1.pl P1_SELECTION P3_RECEIPTS P2_RECOVERY\n";
my ($selection, $receipts, $recovery) = @ARGV;
-f $_ or die "tool file missing\n" for @ARGV;
umask 0077;
my $dir = tempdir('p7-integration-XXXXXX', TMPDIR => 1, CLEANUP => 1);
my $j = JSON::PP->new->canonical(1);
my ($serial, $calls, $cases) = (0, 0, 0);
sub path { "$dir/" . ++$serial . '.json' }
sub save {
    my ($d) = @_;
    my $p = path();
    open my $f, '>:raw', $p or die "fixture creation failed\n";
    print {$f} $j->encode($d), "\n" or die "fixture write failed\n";
    close $f or die "fixture close failed\n";
    return $p;
}
sub load {
    open my $f, '<:raw', $_[0] or die "result missing\n";
    my $d = $j->decode(do { local $/; <$f> });
    close $f;
    return $d;
}
sub invoke {
    ++$calls;
    open my $f, '-|', $^X, @_ or die "cannot start tool\n";
    my $out = do { local $/; <$f> } // '';
    my $ok = close $f;
    $ok or die "tool failed during integration\n";
    return $out;
}
sub report {
    my ($mode, $d) = @_;
    my $in = save($d); my $out = path();
    invoke($selection, $mode, $in, $out);
    return load($out);
}
sub plan {
    my ($tool, $d, @args) = @_;
    return $j->decode(invoke($tool, save($d), @args));
}
sub check { $_[0] or die "integration assertion failed: $_[1]\n" }
sub same { $j->encode($_[0]) eq $j->encode($_[1]) }
sub has { my ($l, $s) = @_; scalar grep { $_ == $s } @$l }

my $good = [1,2,3,4,5];
my @fixtures = (
    { branch=>'one_to_three', lists=>[$good], sources=>[],
      ranges=>[[1,2,3,4],[1,2,3,4],$good] },
    { branch=>'one_to_three', lists=>[$good,[1,2,3,6,7]], sources=>[6],
      ranges=>[[1,2,3,4],[1,2,3,6],[1,2,3,6,7]] },
    { branch=>'one_to_three', lists=>[$good,[1,2,3,6,7],[1,4,5,6,7]], sources=>[6,7],
      ranges=>[[1,2,3,4],[1,2,3,6],[1,4,5,6,7]] },
    { branch=>'four_intersection', lists=>[$good,[1,2,3,4,6],[1,4,5,6,7],[2,3,4,6,8]], sources=>[6,7,8],
      ranges=>[[1,2,3,4],[1,4,5,6],[2,3,4,6,8]] },
    { branch=>'A_in_four', lists=>[$good,[1,2,3,6,7],[1,4,5,6,7],[1,2,4,6,8]], sources=>[6,7,8],
      ranges=>[$good] },
    { branch=>'A_in_three', lists=>[$good,[1,2,3,6,7],[1,4,5,6,7],[2,3,4,6,8]], sources=>[6,7,8],
      ranges=>[[2,3,4,6]] },
);
for my $fixture (@fixtures) {
    my $baseline;
    for my $merlin (@$good) {
        my @sources = ($merlin, @{$fixture->{sources}});
        my %r;
        for my $seat (1..8) {
            my @verified;
            for my $i (0..$#{$fixture->{lists}}) {
                my $l = $fixture->{lists}[$i];
                push @verified, {list=>$l, source=>$sources[$i]} if has($l, $seat);
            }
            # The Merlin's own list is included here as a verified local state.
            $r{$seat} = report('receipt', {v=>1,game=>'p7-fixture',seat=>$seat,verified=>\@verified});
            check(join(',',sort keys %{$r{$seat}}) eq 'four_choice,game,lists,phase,seat,v', 'public receipt fields');
        }
        my $d = {game=>'p7-fixture',receipts=>\%r};
        my $p = plan($receipts, $d, 1, 0);
        check($p->{status} eq 'ready' && $p->{branch} eq $fixture->{branch}, 'branch');
        check(same($p->{ranges}, $fixture->{ranges}), 'ranges');
        my $transcript = {receipts=>\%r, plan=>$p};
        if ($fixture->{branch} eq 'A_in_three') {
            my $x = $fixture->{lists}[3];
            my %sources_report = map {
                $_=>{v=>1,game=>'p7-fixture',phase=>'x_source',seat=>$_,X=>$x,source=>8}
            } @$x;
            my $d2 = {game=>'p7-fixture',retained=>$fixture->{lists},reports=>\%sources_report};
            my $waiting = plan($recovery, $d2);
            check($waiting->{status} eq 'await_A_next_circle', 'four-report recovery waits');
            my $choice = report('recovery', {
                v=>1,game=>'p7-fixture',seat=>1,
                verified=>[map {{list=>$fixture->{lists}[$_],source=>$sources[$_]}} 0..2],
                recovery=>{X=>$x,excluded_source=>8},
            });
            check(join(',',sort keys %$choice) eq 'X,choice,excluded_source,game,phase,seat,v', 'public choice fields');
            my $ready = plan($recovery, {%$d2,a_choice=>$choice}, 2, 0);
            check($ready->{status} eq 'ready' && same($ready->{ranges}, [$good]), 'selection -> recovery interface');
            $transcript->{agreement} = {waiting=>$waiting,choice=>$choice,ready=>$ready};
            # Honest X members report source 8; the two bad members report 6.
            $sources_report{$_}{source}=6 for 6,8;
            my $split = plan($recovery, $d2, 2, 0);
            check($split->{branch} eq 'unsplit_partition' && same($split->{ranges}, [[1,2,3,4],$good]), 'partition recovery');
            $transcript->{partition} = $split;
        }
        my $bytes = $j->encode($transcript);
        $baseline //= $bytes;
        check($bytes eq $baseline, 'public JSON changes when only Merlin position changes');
        ++$cases;
    }
}
print "PASS: $cases synthetic fixture/role cases; $calls actual tool invocations; six list-count/branch fixtures; both X recovery paths; byte-identical public JSON across five Merlin positions\n";
