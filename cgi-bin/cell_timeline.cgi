#!/usr/bin/env perl

use warnings;
use strict;

=head1 NAME

B<cell_timeline.cgi> - Display the disordered architecture for a specified SUPERFAMILY protein.

=head1 DESCRIPTION

Outputs an SVG rendering of the given proteins structual and disordered architecture. Weaker hits are included with their e-values specified as 'hanging' blocks.

An example use of this script is as follows:

To emulate SUPERFAMILY genome page style figures as closely as possible include something similar to the following in the page:

<div width="100%" style="overflow:scroll;">
	<object width="100%" height="100%" data="/cgi-bin/cell_timeline.cgi?proteins=3385949&genome=at&supfam=1&ruler=0" type="image/svg+xml"></object>
</div>

To have super duper Matt style figures do something like:

<div width="100%" style="overflow:scroll;">
	<object width="100%" height="100%" data="/cgi-bin/cell_timeline.cgi?proteins=3385949,26711867&callouts=1&ruler=1&disorder=1" type="image/svg+xml"></object>
</div>


=head1 TODO

B<HANDLE PARTIAL HITS!>

I<SANITIZE INPUT MORE!>

	* Specify lists of proteins, along with other search terms like comb string, required by SUPERFAMILY.

=head1 AUTHOR

B<Matt Oates> - I<Matt.Oates@bristol.ac.uk>

=head1 NOTICE

B<Matt Oates> (Jan 2012) First features added.

=head1 LICENSE AND COPYRIGHT

B<Copyright 2012 Matt Oates>

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.

=head1 FUNCTIONS

=over 4

=cut

use POSIX qw/ceil floor/;
use CGI;
use CGI::Carp qw(fatalsToBrowser); #Force error messages to be output as HTML
use Data::Dumper;
use DBI;
use lib 'lib';
use Utils::SQL::Connect qw/:all/;
use Supfam::Utils qw(:all);


#Deal with the CGI parameters here
my $cgi = CGI->new;

my $lim = $cgi->param('lim');
unless(defined($lim)){
        $lim =20;
}

my $genome = $cgi->param('genome');
unless(defined($genome)){
        $genome = 'hs';
}

my $exp = $cgi->param('exp');
unless(defined($exp)){
        $exp = 2622;
}
my $sort = $cgi->param('sort');
unless(defined($sort)){
        $sort = 'desc';
}
my @exps;
my $like = $cgi->param('like');
my $order = $cgi->param('order');
if(defined($like)){
	my $dbh = dbConnect('trap');
	my $sth = $dbh->prepare("select experiment_id from experiment where sample_name like '%"."$like"."%' and genome = ?;");
	$sth->execute($genome);
	while( my ($exp_id)=  $sth->fetchrow_array()){ 
		push (@exps,$exp_id);
	}
}elsif(defined($order)){
	if(defined($sort)){
	my $dbh = dbConnect('trap');
	my $sth = $dbh->prepare("select experiment_id from snapshot_evolution where genome = 'hs' and label =? order by proportion $sort limit ?;");
	$sth->execute($order,$lim);
	while( my ($exp_id)=  $sth->fetchrow_array()){ 
		push (@exps,$exp_id);
	}
	}
}else{
	@exps = split(/,/,$exp);
}

=item B<get_exp_name>
=cut
sub get_exp_name {
	my $exp = shift;
	my $dbh = dbConnect('trap');
	my $sth = $dbh->prepare('select sample_name from experiment where experiment_id = ?;');
	$sth->execute($exp);
	my $name;
	while( my @temp =  $sth->fetchrow_array()){ 
		$name = $temp[0];
	}
	return $name;
}


=item B<get_timeline>
=cut
sub get_times {
	my $exp = shift;
	my @exps = @{$exp};
	my %times;
	foreach $exp (@exps){
	my $dbh = dbConnect('trap');
	my $sth = $dbh->prepare('select distance,label,proportion from snapshot_evolution where experiment_id = ?;');
	$sth->execute($exp);
	
	my $results=[];	
	while(my ($distance,$label,$proportion)=  $sth->fetchrow_array()){
		$times{$exp}{$distance}{'label'} = $label;
		$times{$exp}{$distance}{'size'} = $proportion;
	}
	}
	return \%times;
}

sub get_norm_times {
	my $dbh = dbConnect('trap');
	my $sth = $dbh->prepare('select distance,max(proportion),min(proportion),std(proportion) from snapshot_evolution where genome =\'hs\' group by distance; ');
	$sth->execute();
	my %norm_times;
	while(my ($distance,$max,$min,$std)=  $sth->fetchrow_array()){
		$norm_times{$distance}{'max'} = $max;
		$norm_times{$distance}{'min'} = $min;
		$norm_times{$distance}{'std'} = $std;
	}
	return \%norm_times;
}

=item B<draw_timeline>
=cut
sub draw_timeline {
	my ($width,$height,$times,$norms) = @_;
	my $diagram = '';
	my $points = scalar(keys %{$norms});
	my $inc = $width/($points+2);
	my $no_samples = scalar(keys %{$times});
	my $timeline_y = $height-(6*$inc);
	
	my $tick_height = 10;

	my $scale_y = $height-(5*$inc);
	#Draw header
	$diagram .= <<EOF
<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" 
	 "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="$width" height="$height"
     viewBox="0 0 $width $height">
EOF
    ;
	
	#Draw the time and scale lines

	$diagram .= <<EOF
	<line x1="0" y1="$scale_y" x2="$width" y2="$scale_y" style="stroke: #333; stroke-width: 1;" />
EOF
	;

my %times = %{$times};
my $done = 0;
foreach my $exp (keys %times)	{
	my $name = get_exp_name($exp);
		#Draw the time and scale lines
	my $up = $timeline_y+($inc/2);
	my $down = $timeline_y-($inc/2);
	$diagram .= <<EOF
	<line x1="0" y1="$timeline_y" x2="$width" y2="$timeline_y" style="stroke: #333; stroke-width: 1;" />
	<line x1="0" y1="$up" x2="$width" y2="$up" style="stroke-opacity: 0.2;stroke: #333; stroke-width: 1;" />
	<line x1="0" y1="$down" x2="$width" y2="$down" style="stroke-opacity: 0.2;stroke: #333; stroke-width: 1;" />
EOF
	;
	
	    
		#Draw the labels
		$diagram .= <<EOF
		<a xlink:href="cell_timeline.cgi?exp=$exp">
		<text x="10" y="$down" text-anchor="right" style="font-size:25px">$name</text>
		</a>
EOF
		;
	
	#Foreach point in time draw the tickmark/label on the scale and the circle on the timeline
	my $dx = 0;
	
	foreach my $time (sort {$a <=> $b} keys %{$times{$exp}}) {
		$dx = $dx + $inc;
		my $dy = $scale_y + $tick_height;
		if($done == 0){
		#Draw scalebar tick marks
		$diagram .= <<EOF
	<line x1="$dx" y1="$scale_y" x2="$dx" y2="$dy" style="stroke: #333; stroke-width: 1;" />
	<line x1="$dx" y1="$scale_y" x2="$dx" y2="$inc" style="stroke: #333; stroke-width: 1; opacity: 0.01" />
EOF
		;
		
		my $label =  $times{$exp}{$time}{'label'};
		#Draw the labels
		my $font = 10;
		my $rotate = $dy - ($font/2);
		$diagram .= <<EOF
		<a xlink:href="cell_timeline.cgi?order=$label">
		<text x="$dx" y="$dy" text-anchor="right" style="font-size:20px" transform="rotate(90 $dx,$rotate)">$label</text>
		</a>
EOF
		;
		
		}

			
		
		my $color;
		my $size;
		my $barw =20;
		my $bar_y = $timeline_y;
		if($times->{$exp}{$time}{'size'} > 0){
			if(($norms->{$time}{'max'} == 0)||($times{$exp}{$time}{'size'} == 0)){
				$size = 0;
			}else{
			$size = (abs(($times{$exp}{$time}{'size'}/$norms->{$time}{'max'})*($inc/2)));
			}
			$color = 'cyan';
			$bar_y = $bar_y - $size;
		}else{
			$color = 'red';
			if(($norms->{$time}{'min'} == 0)||($times{$exp}{$time}{'size'} == 0)){
				$size = 0;
			}else{
			$size = abs($times{$exp}{$time}{'size'}/$norms->{$time}{'min'})*($inc/2);
			}
		}
		#Draw the circles
		my $l = $times{$exp}{$time}{'label'};
		
		my $barx = $dx-($barw/2);
		$diagram .= <<EOF
		<a xlink:href="sample_archs.cgi?label=$l&amp;sample_id=$exp">
		<rect x="$barx" y="$bar_y" height="$size" width="20" fill="$color" opacity="0.6"/>
		</a>
EOF
	}
	$done = 1;
	$timeline_y = $timeline_y - (2*$inc)
}
	
	$diagram .= "\n</svg>";

	return $diagram;
}

my $times = get_times(\@exps);
my $norm_times = get_norm_times();

my $points = scalar(keys %{$norm_times});
my $no_samples = scalar(keys %{$times});
my $width = 1000;
my $inc = $width/($points+2);
my $height = ($no_samples*$inc*2)+(6*$inc);
print $cgi->header("image/svg+xml");
print draw_timeline($width,$height,$times,$norm_times);

=back
=cut

1;
