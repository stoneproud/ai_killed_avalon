#!/usr/bin/env perl
use strict;
use warnings;
use JSON::PP;
# Public metadata only; no Git, network, keys, decryption, or automatic actions.
my $j = JSON::PP->new->canonical(1);
sub need { die "first-window: $_[1]\n" unless $_[0] }
sub scalar_is { defined($_[0]) && !ref($_[0]) && $_[0] eq $_[1] }
sub pin {
    my ($game,$window,$template,$snapshot,$b) = @_;
    need(defined($game) && $game =~ /\A[A-Za-z0-9_-]{1,32}\z/, 'invalid game');
    need(defined($window) && index($window,$game.'_')==0 && $window =~ /\A[A-Za-z0-9_]+\z/, 'invalid window prefix');
    need(defined($template) && $template =~ m{\Aartifacts/[A-Za-z0-9_-]+\{seat\}[A-Za-z0-9_.-]*\.json\z}, 'template must name one artifacts JSON per seat');
    need(defined($snapshot) && $snapshot =~ /\A[0-9a-f]{40}\z/, 'public snapshot hash required');
    need(ref($b) eq 'HASH' && ref($b->{events}) eq 'ARRAY' && ref($b->{files}) eq 'ARRAY', 'bulletin events/files required');
    my (%first,@later);
    for my $e (@{$b->{events}}) {
        next unless ref($e) eq 'HASH'
            && defined($e->{stage}) && !ref($e->{stage}) && index($e->{stage},$window)==0;
        my $s=$e->{by};
        next unless defined($s) && !ref($s) && $s =~ /\A[1-8]\z/;
        if (exists $first{$s}) { push @later, $e->{event_id}//''; next }
        # Freeze the host event BEFORE testing content or finding any attachment.
        $first{$s}=$e;
    }
    my @slots;
    for my $s (1..8) {
        my $p=$template; $p =~ s/\{seat\}/$s/;
        my $r={seat=>$s,source_path=>$p,status=>'no_first_event'};
        my $e=$first{$s};
        if ($e) {
            $r->{event_id}=$e->{event_id}//'';
            $r->{stage}=$e->{stage};
            $r->{branch_commit}=$e->{branch_commit}//'';
            $r->{status}='missing_attachment';
            my @f=grep {ref($_) eq 'HASH' && scalar_is($_->{from},$s)
                && scalar_is($_->{source_commit},$e->{branch_commit})
                && scalar_is($_->{source_path},$p)} @{$b->{files}};
            if (@f==1) {
                my $f=$f[0];
                if ($r->{branch_commit} =~ /\A[0-9a-f]{40}\z/
                    && defined($f->{sha256}) && !ref($f->{sha256}) && $f->{sha256} =~ /\A[0-9a-f]{64}\z/
                    && defined($f->{path}) && !ref($f->{path}) && $f->{path} eq "public/files/p$s/$p") {
                    $r->{status}='pinned_reference';
                    @$r{qw(path sha256 bytes)}=@$f{qw(path sha256 bytes)};
                } else { $r->{status}='invalid_index' }
            } elsif (@f>1) { $r->{status}='ambiguous_index' }
        }
        push @slots,$r;
    }
    return {v=>1,game=>$game,window=>$window,snapshot=>$snapshot,template=>$template,
        slots=>\@slots,ignored_later_events=>\@later,
        note=>'References only; verify pinned bytes, packet context, signatures and openings separately. Never replace an invalid first slot with a later event.'};
}
if (@ARGV==1 && $ARGV[0] eq '--self-test') {
    my $commit='a'x40; my $snapshot='b'x40;
    my $first={event_id=>'first',game_id=>'test',stage=>'test_offer_p5',by=>5,
        branch_commit=>$commit,message=>{seat=>1}};
    my $later={%$first,event_id=>'later',branch_commit=>'c'x40};
    my $f={from=>5,source_commit=>'c'x40,source_path=>'artifacts/test_offer_p5.json',
        path=>'public/files/p5/artifacts/test_offer_p5.json',sha256=>'d'x64,bytes=>1};
    my $b={events=>[$first,$later],files=>[$f]};
    my $p=pin('test','test_offer_','artifacts/test_offer_p{seat}.json',$snapshot,$b);
    need($p->{slots}[4]{event_id} eq 'first' && $p->{slots}[4]{status} eq 'missing_attachment','later packet replaced first missing packet');
    need($p->{slots}[0]{status} eq 'no_first_event','message seat overrode host by');
    $f->{source_commit}=$commit;
    $p=pin('test','test_offer_','artifacts/test_offer_p{seat}.json',$snapshot,$b);
    need($p->{slots}[4]{status} eq 'pinned_reference' && @{$p->{ignored_later_events}}==1,'first attachment not pinned');
    $f->{sha256}='bad';
    need(pin('test','test_offer_','artifacts/test_offer_p{seat}.json',$snapshot,$b)->{slots}[4]{status} eq 'invalid_index','invalid first index not blocked');
    $f->{sha256}='d'x64; push @{$b->{files}},{%$f};
    need(pin('test','test_offer_','artifacts/test_offer_p{seat}.json',$snapshot,$b)->{slots}[4]{status} eq 'ambiguous_index','ambiguous first index accepted');
    $first->{stage}='old_offer_p5'; $later->{stage}='test_other_p5';
    need(pin('test','test_offer_','artifacts/test_offer_p{seat}.json',$snapshot,$b)->{slots}[4]{status} eq 'no_first_event','old game/wrong window included');
    print "PASS: immutable first slot, host attribution, later replacement rejection, malformed/ambiguous index, game/window isolation\n";
    exit;
}
@ARGV==5 or die "usage: perl p5_first_window_v1.pl GAME WINDOW_PREFIX 'artifacts/g2_offer_p{seat}.json' PUBLIC_SNAPSHOT BULLETIN.json | --self-test\n";
my ($game,$window,$template,$snapshot,$path)=@ARGV;
open my $f,'<:raw',$path or die "cannot read public bulletin\n";
my $b=$j->decode(do {local $/;<$f>}); close $f;
print $j->encode(pin($game,$window,$template,$snapshot,$b)),"\n";
