#!/usr/bin/env perl
use strict;
use warnings;

# Exhaustive checks of the combinatorial claims in the accompanying proposal.
# No cryptographic or anonymity proof is claimed by this program.
my @bits = map { 1 << $_ } 0..7;
my @count = (0);
for (1..255) { $count[$_] = $count[$_ >> 1] + ($_ & 1); }
my @five = grep { $count[$_] == 5 } 0..255;
my %key;
for my $m (@five) { $key{$m} = join('', map { $_+1 } grep { $m & (1 << $_) } 0..7); }
my ($configs, $distinct4, $intersection4, $all4, $three, $partitions) = (0)x6;
for my $good (@five) {
    my @bad = grep { !($good & $_) } @bits;
    my @choices = map { my $b=$_; [grep { $_ & $b } @five] } @bad;
    for my $l0 (@{$choices[0]}) {
        for my $l1 (@{$choices[1]}) {
            for my $l2 (@{$choices[2]}) {
                ++$configs;
                my %unique = map { $_ => 1 } ($good,$l0,$l1,$l2);
                next unless keys(%unique) == 4;
                ++$distinct4;
                my @lists = map { 0+$_ } sort { $key{$a} cmp $key{$b} } keys %unique;
                my $pair = 0;
                for my $i (0..2) {
                    for my $j ($i+1..3) {
                        next unless $count[$lists[$i] & $lists[$j]] == 4;
                        $pair = 1;
                        # If either list is true, their intersection is all good.
                        if ($lists[$i] == $good || $lists[$j] == $good) {
                            die 'bad intersection of true list' if (($lists[$i]&$lists[$j]) & (255^$good));
                        }
                    }
                }
                if ($pair) { ++$intersection4; next; }
                my ($abit) = grep { my $b=$_; (grep { $_ & $b } @lists) >= 3 } @bits;
                defined $abit or die 'no A';
                my @with_a = grep { $_ & $abit } @lists;
                # For any possible Merlin in the true list, the source rule must select G.
                for my $merlin (grep { $good & $_ } @bits) {
                    my $sources = $merlin | $bad[0] | $bad[1] | $bad[2];
                    my @selected = grep { $count[$_ & $sources] == 1 } @lists;
                    @selected == 1 && $selected[0] == $good or die "source selector failure: good=$good sources=$sources lists=@lists selected=@selected\n";
                }
                if (@with_a == 4) {
                    ++$all4;
                    $good & $abit or die 'A in all four is not good';
                    next;
                }
                ++$three;
                my ($x) = grep { !($_ & $abit) } @lists;
                next if $x == $good; # True X cannot fail, so no source disclosure.
                $good & $abit or die 'A not good after false X fails';
                my @remaining = grep { $_ != $x } @lists;
                my $honest_in_x = $x & $good;
                my @xbits = grep { $x & $_ } @bits;
                for my $i (0..3) {
                    for my $j ($i+1..4) {
                        my $two = $xbits[$i] | $xbits[$j];
                        my $three_group = $x ^ $two;
                        # All truthful source reporters lie in one unsplit report group.
                        next unless ($honest_in_x & $two) == $honest_in_x
                            || ($honest_in_x & $three_group) == $honest_in_x;
                        ++$partitions;
                        my @kept = grep { !($_ & $two) || !($_ & $three_group) } @remaining;
                        @kept >= 1 && @kept <= 2 && (grep { $_ == $good } @kept)
                            or die 'partition filter loses true list or keeps too many';
                    }
                }
            }
        }
    }
}
my $paths = 0;
sub tasks {
    my ($clean, $q, $range, $success, $failure) = @_;
    if ($success == 3) { ++$paths; return; }
    die 'three failures possible' if $failure == 3;
    die 'out of tasks' if $q > 5;
    # A clean four-person range remains safe under quest-4's one-extra-person rule.
    tasks($clean,$q+1,$range,$success+1,$failure);
    tasks($clean,$q+1,$range+1,$success,$failure+1) unless $clean & (1 << $range);
}
for my $clean (1..7) { tasks($clean,1,0,0,0); }
print "PASS: $configs issuer/list configurations; $distinct4 with four distinct lists\n";
print "Four-list branches: intersection=$intersection4; A-in-four=$all4; A-in-three=$three\n";
print "Checked $partitions admissible unsplit partitions and all five possible Merlin locations\n";
print "PASS: $paths adversarial task-outcome paths for three ranges with at least one clean range\n";
