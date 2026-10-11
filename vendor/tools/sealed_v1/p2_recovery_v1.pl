#!/usr/bin/env perl
use strict;
use warnings;
use JSON::PP;

# Public inputs only. Host event attribution and an actual failed X are external
# preconditions. Never put private source maps, keys or openings into this input.
my $json = JSON::PP->new->canonical(1);
sub eqv { defined($_[0]) && !ref($_[0]) && $_[0] eq $_[1] }
sub seats { my ($m)=@_; return [grep {$m & (1 << ($_-1))} 1..8] }
sub key { join(',', @{seats($_[0])}) }
sub count { scalar @{seats($_[0])} }
sub mask {
    my ($v)=@_; return undef unless ref($v) eq 'ARRAY' && @$v == 5;
    my ($m,$last)=(0,0);
    for my $s (@$v) {
        return undef unless defined($s) && !ref($s) && $s =~ /\A[1-8]\z/ && $s > $last;
        $m |= 1 << ($s-1); $last=$s;
    }
    return $m;
}
sub small4 { my $s=seats($_[0]); return [@$s[0..3]] }
sub recover {
    my ($d)=@_;
    ref($d) eq 'HASH' or die "input object required\n";
    my $game=$d->{game};
    defined($game) && !ref($game) && $game =~ /\A[A-Za-z0-9_-]{1,32}\z/
        or die "valid game required\n";
    ref($d->{retained}) eq 'ARRAY' && @{$d->{retained}} == 4
        or die "four original retained lists required\n";
    my @lists=map {mask($_)} @{$d->{retained}};
    !grep {!defined($_)} @lists or die "invalid retained list\n";
    my %unique=map {$_=>1} @lists;
    keys(%unique)==4 or die "distinct retained lists required\n";
    @lists=sort {key($a) cmp key($b)} @lists;
    for my $i (0..2) { for my $j ($i+1..3) {
        count($lists[$i] & $lists[$j]) < 4 or die "not the X-recovery branch\n";
    }}
    my ($anchor)=grep {my $bit=1 << ($_-1); (grep {$_ & $bit} @lists)>=3} 1..8;
    defined($anchor) or die "no A\n";
    my $abit=1 << ($anchor-1);
    (grep {$_ & $abit} @lists)==3 or die "A must occur in exactly three lists\n";
    my ($x)=grep {!($_ & $abit)} @lists;
    my @rest=grep {$_ != $x} @lists;
    ref($d->{reports}) eq 'HASH' or die "reports object required\n";
    my (%groups,@ignored);
    for my $s (@{seats($x)}) {
        my $r=$d->{reports}{$s}; my $f;
        if (ref($r) eq 'HASH' && eqv($r->{v},1) && eqv($r->{game},$game)
                && eqv($r->{phase},'x_source') && eqv($r->{seat},$s)) {
            my $rx=mask($r->{X});
            if (defined($rx) && $rx==$x && defined($r->{source})
                    && !ref($r->{source}) && $r->{source} =~ /\A[1-8]\z/
                    && ($x & (1 << ($r->{source}-1)))) { $f=0+$r->{source} }
        }
        # Each invalid/missing report is its own indivisible singleton.
        push @{$groups{defined($f) ? "source:$f" : "missing:$s"}},$s;
        push @ignored,$s unless defined($f);
    }
    my $p={game=>$game,A=>$anchor,X=>seats($x),ignored_reports=>\@ignored,ranges=>[],
        premise=>'X actually failed; five honest players followed the fixed protocol'};
    my ($common)=sort grep {@{$groups{$_}}>=4} keys %groups;
    if (defined($common)) {
        my ($f)=$common =~ /\Asource:([1-8])\z/;
        defined($f) or die "impossible missing-report consensus\n";
        $p->{branch}='four_source_agreement'; $p->{source}=0+$f;
        my $r=$d->{a_choice}; my $chosen;
        if (ref($r) eq 'HASH' && eqv($r->{v},1) && eqv($r->{game},$game)
                && eqv($r->{phase},'x_choice') && eqv($r->{seat},$anchor)
                && eqv($r->{excluded_source},$f)) {
            my $rx=mask($r->{X}); my $c=mask($r->{choice});
            $chosen=$c if defined($rx) && $rx==$x && defined($c)
                && (grep {$_==$c} @rest);
        }
        if (defined($chosen)) {
            $p->{status}='ready'; $p->{ranges}=[seats($chosen)];
            $p->{note}='A is honest after failed X; private source calculation remains a premise';
        } else {
            $p->{status}='await_A_next_circle';
            $p->{note}='A publishes only the unique list, never the remaining private sources';
        }
        return $p;
    }
    my @groups=map {$groups{$_}} sort keys %groups;
    my @pairs;
    for my $selection (0..(1 << @groups)-1) {
        my @members;
        for my $i (0..$#groups) {push @members,@{$groups[$i]} if $selection & (1 << $i)}
        next unless @members==2;
        my $two=0; $two |= 1 << ($_-1) for @members;
        push @pairs,$two;
    }
    @pairs or die "no unsplit 2+3 partition; protocol premises failed\n";
    my ($two)=sort {key($a) cmp key($b)} @pairs;
    my $three=$x ^ $two;
    my @kept=grep {!($_ & $two) || !($_ & $three)} @rest;
    @kept>=1 && @kept<=2 or die "filtered list count violates premises\n";
    $p->{branch}='unsplit_partition'; $p->{status}='ready';
    $p->{two}=seats($two); $p->{three}=seats($three);
    $p->{retained_after_recovery}=[map {seats($_)} @kept];
    $p->{ranges}=[small4($kept[0]),seats($kept[-1])];
    return $p;
}
sub task_team {
    my ($p,$q,$failed)=@_;
    $p->{status} eq 'ready' or die "recovery not ready\n";
    $q =~ /\A[2-5]\z/ or die "recovery quest must be 2..5\n";
    $failed =~ /\A[0-1]\z/ && $failed < @{$p->{ranges}}
        or die "recovery range exhausted\n";
    my @scope=@{$p->{ranges}[$failed]}; my $size=(3,4,4,5,5)[$q-1];
    return [@scope[0..$size-1]] if @scope >= $size;
    if ($q==4 && @scope==4) {
        my %in=map {$_=>1} @scope; my ($extra)=grep {!$in{$_}} 1..8;
        return [sort {$a<=>$b} (@scope,$extra)];
    }
    die "quest 5 requires full five-person range\n";
}
sub assert {die "self-test failed: $_[1]\n" unless $_[0]}
sub selftest {
    my $lists=[[1,2,3,4,5],[1,2,3,6,7],[1,4,5,6,7],[2,3,4,6,8]];
    my $x=mask($lists->[3]); my $tested=0;
    for my $truth (@$lists[0..2]) {
        my $good=mask($truth); my @bad=grep {!($good & (1 << ($_-1)))} @{seats($x)};
        for my $f (@bad) {
            my @options=(undef,@{seats($x)});
            for my $code (0..6**@bad-1) {
                my (%reports,$n); $n=$code;
                for my $s (@{seats($x)}) {
                    $reports{$s}={v=>1,game=>'test',phase=>'x_source',seat=>$s,X=>seats($x),source=>$f};
                }
                for my $s (@bad) {$reports{$s}{source}=$options[$n%6]; $n=int($n/6)}
                my $d={game=>'test',retained=>$lists,reports=>\%reports};
                my $p=recover($d);
                if ($p->{status} eq 'ready') {
                    assert(scalar(grep(mask($_)==$good,@{$p->{retained_after_recovery}})),'true list retained');
                    assert(@{$p->{ranges}}==2,'two fallback ranges');
                } else {
                    assert($p->{source}==$f && $p->{status} eq 'await_A_next_circle','honest consensus');
                    $d->{a_choice}={v=>1,game=>'test',phase=>'x_choice',seat=>1,X=>seats($x),
                        excluded_source=>$f,choice=>$truth};
                    my $ready=recover($d);
                    assert($ready->{status} eq 'ready' && mask($ready->{ranges}[0])==$good,'A output');
                }
                ++$tested;
            }
        }
    }
    my $p=recover({game=>'test',retained=>$lists,reports=>{}});
    assert(@{$p->{ignored_reports}}==5 && $p->{status} eq 'ready','missing reports stay separate');
    assert($json->encode($p->{two}) eq '[2,3]','lexicographically first pair');
    my %r=map {$_=>{v=>1,game=>'test',phase=>'x_source',seat=>$_,X=>seats($x),source=>6}} @{seats($x)};
    my $d={game=>'test',retained=>$lists,reports=>\%r,
        a_choice=>{v=>1,game=>'test',phase=>'x_choice',seat=>1,X=>seats($x),
            excluded_source=>6,choice=>$lists->[0]}};
    assert(recover($d)->{status} eq 'ready','bound A choice');
    for my $bad ([game=>'old'],[seat=>2],[phase=>'x_source'],[excluded_source=>8],
            [X=>$lists->[0]],[choice=>$lists->[3]]) {
        my %copy=%{$d->{a_choice}}; $copy{$bad->[0]}=$bad->[1];
        assert(recover({%$d,a_choice=>\%copy})->{status} eq 'await_A_next_circle','invalid A choice');
    }
    $r{8}{source}=1;
    assert($json->encode(recover($d)->{ignored_reports}) eq '[8]','source must belong to X');
    $p->{ranges}=[[1,2,3,4],[1,2,3,4,5]];
    assert($json->encode(task_team($p,4,0)) eq '[1,2,3,4,5]','quest 4 supplement');
    assert($json->encode(task_team($p,5,1)) eq '[1,2,3,4,5]','quest 5 range');
    my $ok=eval {task_team($p,5,0);1}; assert(!$ok,'no four-person quest 5');
    print "PASS: $tested adversarial source reports, missing singletons, A output, task sizes\n";
}
if (@ARGV==1 && $ARGV[0] eq '--self-test') {selftest();exit}
@ARGV>=1 && @ARGV<=3 or die "usage: perl p2_recovery_v1.pl INPUT.json [QUEST [RECOVERY_FAILED_RANGES]] | --self-test\n";
open my $f,'<:raw',$ARGV[0] or die "cannot read input: $!\n";
my $d=$json->decode(do {local $/;<$f>}); close $f;
my $p=recover($d);
$p->{team}=task_team($p,$ARGV[1],$ARGV[2]//0) if @ARGV>=2;
print $json->encode($p),"\n";
