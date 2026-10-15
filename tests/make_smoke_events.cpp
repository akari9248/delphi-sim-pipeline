// Synthetic, energy-conserving events for software checks, not physics samples.
// e+e- -> B+ B-, each B -> three pions, with a known 3 mm flight distance.
#include <HepMC3/GenEvent.h>
#include <HepMC3/GenParticle.h>
#include <HepMC3/GenVertex.h>
#include <HepMC3/WriterAscii.h>
#include <HepMC3/WriterAsciiHepMC2.h>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    if (argc != 2) throw std::runtime_error("Expected an output directory");
    const std::string dir = argv[1];
    HepMC3::WriterAscii ascii(dir + "/smoke.hepmc3");
    HepMC3::WriterAsciiHepMC2 legacy(dir + "/smoke.hepmc2");
    HepMC3::WriterAscii scaled(dir + "/smoke_mev_cm.hepmc3");
    constexpr double eb = 45.625, mb = 5.27934, mpi = 0.13957039;
    const double pb = std::sqrt(eb * eb - mb * mb);
    const double beta = pb / eb, gamma = eb / mb;
    for (int n = 0; n < 12; ++n) {
        HepMC3::GenEvent event(HepMC3::Units::GEV, HepMC3::Units::MM);
        event.set_event_number(n + 1);
        auto production = std::make_shared<HepMC3::GenVertex>();
        for (int sign : {-1, 1}) {
            auto beam = std::make_shared<HepMC3::GenParticle>(
                HepMC3::FourVector(0, 0, sign * eb, eb), -sign * 11, 4);
            beam->set_generated_mass(0);
            production->add_particle_in(beam);
        }
        event.add_vertex(production);
        const double phi = 0.2 + n * 0.17;
        for (int sign : {-1, 1}) {
            auto b = std::make_shared<HepMC3::GenParticle>(HepMC3::FourVector(
                sign * pb * std::cos(phi), sign * pb * std::sin(phi), 0, eb), sign * 521, 2);
            b->set_generated_mass(mb);
            production->add_particle_out(b);
            auto decay = std::make_shared<HepMC3::GenVertex>(HepMC3::FourVector(
                sign * 3.0 * std::cos(phi), sign * 3.0 * std::sin(phi), 0, 3.0 / beta));
            decay->add_particle_in(b);
            const double e = mb / 3.0, p = std::sqrt(e * e - mpi * mpi);
            for (int j = 0; j < 3; ++j) {
                const double angle = 0.3 + j * 2.0 * std::acos(-1.0) / 3.0;
                const double parallel = p * std::cos(angle);
                const double transverse = p * std::sin(angle);
                const double longitudinal = gamma * (parallel + sign * beta * e);
                auto pion = std::make_shared<HepMC3::GenParticle>(HepMC3::FourVector(
                    longitudinal * std::cos(phi) - transverse * std::sin(phi),
                    longitudinal * std::sin(phi) + transverse * std::cos(phi),
                    0, gamma * (e + sign * beta * parallel)), (j == 2 ? -sign : sign) * 211, 1);
                pion->set_generated_mass(mpi);
                decay->add_particle_out(pion);
            }
            event.add_vertex(decay);
        }
        ascii.write_event(event);
        legacy.write_event(event);
        event.set_units(HepMC3::Units::MEV, HepMC3::Units::CM);
        scaled.write_event(event);
    }
    ascii.close();
    legacy.close();
    scaled.close();
}
