!*******************************************************************************
! This module include the methods to calculate current densities due to
! different fluid drifts. Not all of currents due to drifts are expressed in
! explicit form to save space. The suffix 1, 2 of each variable indicate two
! different set of data. They can be used to express different kind of currents.
! The energy conversion due to j \cdot E is calculated when the current
! denisities are calculated, since jx, jy, jz are going to be re-used.
!*******************************************************************************
module current_densities
    use constants, only: fp, dp
    use pic_fields, only: bx, by, bz, ex, ey, ez, pxx, pxy, pxz, pyy, &
            pyz, pzz, pyx, pzx, pzy, vx, vy, vz, ux, uy, uz, &
            num_rho, absB, jx, jy, jz
    use para_perp_pressure, only: ppara, pperp
    use neighbors_module, only: ixl, iyl, izl, ixh, iyh, izh, idx, idy, idz
    use jdote_module, only: jdote, calc_jdote
    use mpi_topology, only: htg
    use picinfo, only: domain
    use mpi_io_fields, only: save_field
    use parameters, only: is_rel
    implicit none
    private
    public jx1, jy1, jz1, jx2, jy2, jz2, jagyx, jagyy, jagyz, &
        jperpx1, jperpy1, jperpz1, jperpx2, jperpy2, jperpz2
    public init_current_densities, calc_current_densities, &
           free_current_densities, set_current_densities_to_zero, &
           init_ava_current_densities, free_avg_current_densities, &
           save_averaged_current
    real(fp), allocatable, dimension(:,:,:) :: jx1, jy1, jz1
    real(fp), allocatable, dimension(:,:,:) :: jx2, jy2, jz2
    real(fp), allocatable, dimension(:,:,:) :: jagyx, jagyy, jagyz
    real(fp), allocatable, dimension(:,:,:) :: jperpx1, jperpy1, jperpz1
    real(fp), allocatable, dimension(:,:,:) :: jperpx2, jperpy2, jperpz2
    real(fp), allocatable, dimension(:,:,:) :: javg
    integer, parameter :: ncurrents = 15

    contains

    !---------------------------------------------------------------------------
    ! Initialize current densities.
    !---------------------------------------------------------------------------
    subroutine init_current_densities
        use mpi_topology, only: htg ! The topology with ghost cells.
        implicit none
        integer :: nx, ny, nz

        nx = htg%nx
        ny = htg%ny
        nz = htg%nz

        allocate(jx1(nx,ny,nz))
        allocate(jy1(nx,ny,nz))
        allocate(jz1(nx,ny,nz))
        allocate(jx2(nx,ny,nz))
        allocate(jy2(nx,ny,nz))
        allocate(jz2(nx,ny,nz))
        allocate(jagyx(nx,ny,nz))
        allocate(jagyy(nx,ny,nz))
        allocate(jagyz(nx,ny,nz))
        allocate(jperpx1(nx,ny,nz))
        allocate(jperpy1(nx,ny,nz))
        allocate(jperpz1(nx,ny,nz))
        allocate(jperpx2(nx,ny,nz))
        allocate(jperpy2(nx,ny,nz))
        allocate(jperpz2(nx,ny,nz))

        call set_current_densities_to_zero
    end subroutine init_current_densities

    !---------------------------------------------------------------------------
    ! Initialize the averaged current density.
    !---------------------------------------------------------------------------
    subroutine init_ava_current_densities
        use parameters, only: tp1, tp2
        implicit none
        allocate(javg(3, ncurrents, tp2-tp1+1))
        javg = 0.0
    end subroutine init_ava_current_densities

    !---------------------------------------------------------------------------
    ! Free the averaged current density.
    !---------------------------------------------------------------------------
    subroutine free_avg_current_densities
        implicit none
        deallocate(javg)
    end subroutine free_avg_current_densities

    !---------------------------------------------------------------------------
    ! Set current densities to be zero. It is required for each time step.
    !---------------------------------------------------------------------------
    subroutine set_current_densities_to_zero
        implicit none
        jx1 = 0.0; jy1 = 0.0; jz1 = 0.0
        jx2 = 0.0; jy2 = 0.0; jz2 = 0.0
        jagyx = 0.0; jagyy = 0.0; jagyz = 0.0
        jperpx1 = 0.0; jperpy1 = 0.0; jperpz1 = 0.0
        jperpx2 = 0.0; jperpy2 = 0.0; jperpz2 = 0.0
    end subroutine set_current_densities_to_zero

    !---------------------------------------------------------------------------
    ! Free current densities.
    !---------------------------------------------------------------------------
    subroutine free_current_densities
        implicit none
        deallocate(jx1, jy1, jz1)
        deallocate(jx2, jy2, jz2)
        deallocate(jagyx, jagyy, jagyz)
        deallocate(jperpx1, jperpy1, jperpz1)
        deallocate(jperpx2, jperpy2, jperpz2)
    end subroutine free_current_densities

    !---------------------------------------------------------------------------
    ! Calculate current components from all kinds of drifts.
    ! Input:
    !   ct: current time frame.
    !---------------------------------------------------------------------------
    subroutine calc_current_densities(ct)
        use mpi_module
        use constants, only: fp
        use saving_flags, only: save_jtot, save_jagy, save_jperp1, &
                save_jperp2, save_jagy, save_jtot_dote, save_jagy_dote, &
                save_jperp1_dote, save_jperp2_dote, save_jagy_dote
        use jdote_module, only: jdote_tot
        use mpi_io_fields, only: save_field
        use parameters, only: tp1
        implicit none
        integer, intent(in) :: ct
        integer :: t

        t = ct - tp1 + 1

        ! Current due to agyrotropic pressure.
        call calc_agyrotropy_current

        ! Current due to curvature drift (jcpara) and gyromotion(jcperp).
        call calc_curvature_drift_current(ct, javg(:,1,t), javg(:,2,t), &
                                          jdote_tot(1,t), jdote_tot(2,t))

        ! Current due to perpendicular magnetization.
        call calc_perp_magnetization_current(ct, javg(:,3,t), jdote_tot(3,t))

        ! Current due to gradient B drift.
        call calc_gradientB_drift_current(ct, javg(:,4,t), jdote_tot(4,t))

        ! Current due to diamagnetic drift.
        call calc_diamagnetic_drift_current(ct, javg(:,5,t), jdote_tot(5,t))

        ! Current due to polarization drift.
        call calc_polarization_drift_current(ct, javg(:,6,t), jdote_tot(6,t))

        ! Current due to E cross B drift.
        call calc_exb_drift_current(ct, javg(:,7,t), jdote_tot(7,t))

        ! Current directly from PIC simulations.
        call calc_current_single_fluid(ct, javg(:,8,t), javg(:,9,t), &
            jdote_tot(8,t), jdote_tot(9,t))

        call calc_jdote(jx, jy, jz, jdote_tot(15,t))
        if (save_jtot_dote==1) then
            call save_field(jdote, 'jdote', ct)
        endif

        ! Calculated perpendicular current density using two expressions.
        call calc_jdote(jperpx1, jperpy1, jperpz1, jdote_tot(10,t))
        if (save_jperp1==1) then
            call save_current_density('jperp1', jperpx1, jperpy1, jperpz1, ct)
        endif
        if (save_jperp1_dote==1) then
            call save_field(jdote, 'jperp1_dote', ct)
        endif
        call calc_jdote(jperpx2, jperpy2, jperpz2, jdote_tot(11,t))
        if (save_jperp2==1) then
            call save_current_density('jperp2', jperpx2, jperpy2, jperpz2, ct)
        endif
        if (save_jperp2_dote==1) then
            call save_field(jdote, 'jperp2_dote', ct)
        endif
        call calc_averaged_currents(jx1, jy1, jz1, javg(:,10,t))
        call calc_averaged_currents(jx2, jy2, jz2, javg(:,11,t))

        ! Current for each species calculated directly using q*n*u
        call calc_qnv_current(ct, javg(:,12,t), javg(:,13,t), &
                jdote_tot(12,t), jdote_tot(13,t))

        ! Current due to the compressibility.
        call calc_compression_current(ct, javg(:,15,t), jdote_tot(16,t))

        ! Current due to agyrotropic pressure.
        call calc_jdote(jagyx, jagyy, jagyz, jdote_tot(14,t))
        if (save_jagy==1) then
            call save_current_density('jagy', jagyx, jagyy, jagyz, ct)
        endif
        if (save_jagy_dote==1) then
            call save_field(jdote, 'jagy_dote', ct)
        endif

    end subroutine calc_current_densities

    !---------------------------------------------------------------------------
    ! Electric current due to agyrotropic pressure.
    ! -(\nabla\cdot\tensor{P})\times\vect{B}/B^2+(\nabla\cdot(P_\perp\tensor{I}+
    ! (P_\parallel-P_\perp)))\times\vect{B}/B^2
    ! Here, the divergence of the pressure tensor part is calculated.
    ! This will be updated when other terms are calculated.
    !---------------------------------------------------------------------------
    subroutine calc_agyrotropy_current
        implicit none
        real(fp) :: bx1, by1, bz1, btot1, ib2
        real(fp) :: divpx, divpy, divpz
        integer :: nx, ny, nz, ix, iy, iz

        nx = htg%nx
        ny = htg%ny
        nz = htg%nz

        if (is_rel == 0) then
            do iz = 1, nz
                do iy = 1, ny
                    do ix = 1, nx
                        bx1 = bx(ix, iy, iz)
                        by1 = by(ix, iy, iz)
                        bz1 = bz(ix, iy, iz)
                        btot1 = absB(ix, iy, iz)
                        ib2 = 1.0/(btot1*btot1)
                        divpx = (pxx(ixh(ix),iy,iz)-pxx(ixl(ix),iy,iz))*idx(ix) + &
                                (pxy(ix,iyh(iy),iz)-pxy(ix,iyl(iy),iz))*idy(iy) + &
                                (pxz(ix,iy,izh(iz))-pxz(ix,iy,izl(iz)))*idz(iz)
                        divpy = (pxy(ixh(ix),iy,iz)-pxy(ixl(ix),iy,iz))*idx(ix) + &
                                (pyy(ix,iyh(iy),iz)-pyy(ix,iyl(iy),iz))*idy(iy) + &
                                (pyz(ix,iy,izh(iz))-pyz(ix,iy,izl(iz)))*idz(iz)
                        divpz = (pxz(ixh(ix),iy,iz)-pxz(ixl(ix),iy,iz))*idx(ix) + &
                                (pyz(ix,iyh(iy),iz)-pyz(ix,iyl(iy),iz))*idy(iy) + &
                                (pzz(ix,iy,izh(iz))-pzz(ix,iy,izl(iz)))*idz(iz)
                        jagyx(ix,iy,iz) = -(divpy*bz1-divpz*by1)*ib2
                        jagyy(ix,iy,iz) = -(divpz*bx1-divpx*bz1)*ib2
                        jagyz(ix,iy,iz) = -(divpx*by1-divpy*bx1)*ib2
                    enddo ! x loop
                enddo ! y loop
            enddo ! z loop
        else
            do iz = 1, nz
                do iy = 1, ny
                    do ix = 1, nx
                        bx1 = bx(ix, iy, iz)
                        by1 = by(ix, iy, iz)
                        bz1 = bz(ix, iy, iz)
                        btot1 = absB(ix, iy, iz)
                        ib2 = 1.0/(btot1*btot1)
                        divpx = (pxx(ixh(ix),iy,iz)-pxx(ixl(ix),iy,iz))*idx(ix) + &
                                (pxy(ix,iyh(iy),iz)-pxy(ix,iyl(iy),iz))*idy(iy) + &
                                (pxz(ix,iy,izh(iz))-pxz(ix,iy,izl(iz)))*idz(iz)
                        divpy = (pyx(ixh(ix),iy,iz)-pyx(ixl(ix),iy,iz))*idx(ix) + &
                                (pyy(ix,iyh(iy),iz)-pyy(ix,iyl(iy),iz))*idy(iy) + &
                                (pyz(ix,iy,izh(iz))-pyz(ix,iy,izl(iz)))*idz(iz)
                        divpz = (pzx(ixh(ix),iy,iz)-pzx(ixl(ix),iy,iz))*idx(ix) + &
                                (pzy(ix,iyh(iy),iz)-pzy(ix,iyl(iy),iz))*idy(iy) + &
                                (pzz(ix,iy,izh(iz))-pzz(ix,iy,izl(iz)))*idz(iz)
                        jagyx(ix,iy,iz) = -(divpy*bz1-divpz*by1)*ib2
                        jagyy(ix,iy,iz) = -(divpz*bx1-divpx*bz1)*ib2
                        jagyz(ix,iy,iz) = -(divpx*by1-divpy*bx1)*ib2
                    enddo ! x loop
                enddo ! y loop
            enddo ! z loop
        endif
    end subroutine calc_agyrotropy_current

    !---------------------------------------------------------------------------
    ! Calculate electric current due to curvature drift.
    ! P_\parallel\frac{\vect{B}\times(\vect{B}\cdot\nabla)\vect{B}}{B^4}
    ! A little modification is done here, since the expression above equals to
    ! P_\parallel\frac{\vect{B}\times(\vect{B}\cdot\nabla)(\vect{B}/B)}{B^3}.
    ! Input:
    !   ct: current time frame.
    ! Output:
    !   jcpara_avg, jcperp_avg: the averaged 3 components of electric currents.
    !   jcpara_dote, jcperp_dote: the total j dot E in the box.
    !---------------------------------------------------------------------------
    subroutine calc_curvature_drift_current(ct, jcpara_avg, jcperp_avg, &
                                            jcpara_dote, jcperp_dote)
        use saving_flags, only: save_jcpara, save_jcperp, save_jcpara_dote, &
                save_jcperp_dote
        implicit none
        integer, intent(in) :: ct
        real(fp), intent(out) :: jcpara_dote, jcperp_dote
        real(fp), dimension(3), intent(out) :: jcpara_avg, jcperp_avg
        real(fp) :: bx1, by1, bz1, btot1, ib3, ib4
        integer :: nx, ny, nz, ix, iy, iz
        real(fp) :: curx, cury, curz

        nx = htg%nx
        ny = htg%ny
        nz = htg%nz

        do iz = 1, nz
            do iy = 1, ny
                do ix = 1, nx
                    bx1 = bx(ix, iy, iz)
                    by1 = by(ix, iy, iz)
                    bz1 = bz(ix, iy, iz)
                    btot1 = absB(ix, iy, iz)
                    ib3 = 1.0/(btot1*btot1*btot1)
                    ib4 = ib3 / btot1
                    curx = (bx(ixh(ix),iy,iz) - bx(ixl(ix),iy,iz))*bx1*idx(ix) + &
                           (bx(ix,iyh(iy),iz) - bx(ix,iyl(iy),iz))*by1*idy(iy) + &
                           (bx(ix,iy,izh(iz)) - bx(ix,iy,izl(iz)))*bz1*idz(iz)
                    cury = (by(ixh(ix),iy,iz) - by(ixl(ix),iy,iz))*bx1*idx(ix) + &
                           (by(ix,iyh(iy),iz) - by(ix,iyl(iy),iz))*by1*idy(iy) + &
                           (by(ix,iy,izh(iz)) - by(ix,iy,izl(iz)))*bz1*idz(iz)
                    curz = (bz(ixh(ix),iy,iz) - bz(ixl(ix),iy,iz))*bx1*idx(ix) + &
                           (bz(ix,iyh(iy),iz) - bz(ix,iyl(iy),iz))*by1*idy(iy) + &
                           (bz(ix,iy,izh(iz)) - bz(ix,iy,izl(iz)))*bz1*idz(iz)
                    ! Current due to curvature drift
                    jx1(ix,iy,iz) = -(cury*bz1-curz*by1)*ppara(ix,iy,iz)*ib4
                    jy1(ix,iy,iz) = -(curz*bx1-curx*bz1)*ppara(ix,iy,iz)*ib4
                    jz1(ix,iy,iz) = -(curx*by1-cury*bx1)*ppara(ix,iy,iz)*ib4
                    ! Similar as above, but with perpendicular pressure.
                    ! This term is due to particle gyromotion.
                    jx2(ix,iy,iz) = (cury*bz1-curz*by1)*pperp(ix,iy,iz)*ib4
                    jy2(ix,iy,iz) = (curz*bx1-curx*bz1)*pperp(ix,iy,iz)*ib4
                    jz2(ix,iy,iz) = (curx*by1-cury*bx1)*pperp(ix,iy,iz)*ib4
                enddo
            enddo
        enddo
        jperpx1 = jperpx1 + jx1
        jperpy1 = jperpy1 + jy1
        jperpz1 = jperpz1 + jz1
        jperpx2 = jperpx2 + jx1 + jx2
        jperpy2 = jperpy2 + jy1 + jy2
        jperpz2 = jperpz2 + jz1 + jz2
        jagyx = jagyx - jx1 - jx2
        jagyy = jagyy - jy1 - jy2
        jagyz = jagyz - jz1 - jz2

        jcpara_avg = 0.0
        jcperp_avg = 0.0
        jcpara_dote = 0.0
        jcperp_dote = 0.0

        call calc_jdote(jx1, jy1, jz1, jcpara_dote)
        if (save_jcpara==1) then
            call save_current_density('jcpara', jx1, jy1, jz1, ct)
        endif
        if (save_jcpara_dote==1) then
            call save_field(jdote, 'jcpara_dote', ct)
        endif
        call calc_jdote(jx2, jy2, jz2, jcperp_dote)
        if (save_jcperp==1) then
            call save_current_density('jcperp', jx2, jy2, jz2, ct)
        endif
        if (save_jcperp_dote==1) then
            call save_field(jdote, 'jcperp_dote', ct)
        endif
        call calc_averaged_currents(jx1, jy1, jz1, jcpara_avg)
        call calc_averaged_currents(jx2, jy2, jz2, jcperp_avg)

    end subroutine calc_curvature_drift_current

    !---------------------------------------------------------------------------
    ! Calculate electric current due to perpendicular magnetization.
    ! -\left[\nabla\times\right(\frac{P_\perp\vect{B}}{B^2}\right)]_\perp
    ! Input:
    !   ct: current time frame.
    ! Output:
    !   jmag_avg: the averaged 3 components of electric currents.
    !   jmag_dote: the total j dot E in the box.
    !---------------------------------------------------------------------------
    subroutine calc_perp_magnetization_current(ct, jmag_avg, jmag_dote)
        use saving_flags, only: save_jmag, save_jmag_dote
        implicit none
        integer, intent(in) :: ct
        real(fp), dimension(3), intent(out) :: jmag_avg
        real(fp), intent(out) :: jmag_dote
        real(fp) :: bx1, by1, bz1, btot1, ib2
        real(fp) :: pperpx, pperpy, pperpz, tmp
        integer :: nx, ny, nz, ix, iy, iz

        nx = htg%nx
        ny = htg%ny
        nz = htg%nz
        ! idxh = domain%idxh
        ! idyh = domain%idyh
        ! idzh = domain%idzh

        do iz = 1, nz
            do iy = 1, ny
                do ix = 1, nx
                    bx1 = bx(ix, iy, iz)
                    by1 = by(ix, iy, iz)
                    bz1 = bz(ix, iy, iz)
                    btot1 = absB(ix, iy, iz)
                    ib2 = 1.0/(btot1*btot1)
                    pperpx = (pperp(ix,iyh(iy),iz)*bz(ix,iyh(iy),iz)/absB(ix,iyh(iy),iz)**2 - &
                              pperp(ix,iyl(iy),iz)*bz(ix,iyl(iy),iz)/absB(ix,iyl(iy),iz)**2)*idy(iy) -&
                             (pperp(ix,iy,izh(iz))*by(ix,iy,izh(iz))/absB(ix,iy,izh(iz))**2 - &
                              pperp(ix,iy,izl(iz))*by(ix,iy,izl(iz))/absB(ix,iy,izl(iz))**2)*idz(iz)
                    pperpy = (pperp(ix,iy,izh(iz))*bx(ix,iy,izh(iz))/absB(ix,iy,izh(iz))**2 - &
                              pperp(ix,iy,izl(iz))*bx(ix,iy,izl(iz))/absB(ix,iy,izl(iz))**2)*idz(iz) -&
                             (pperp(ixh(ix),iy,iz)*bz(ixh(ix),iy,iz)/absB(ixh(ix),iy,iz)**2 - &
                              pperp(ixl(ix),iy,iz)*bz(ixl(ix),iy,iz)/absB(ixl(ix),iy,iz)**2)*idx(ix)
                    pperpz = (pperp(ixh(ix),iy,iz)*by(ixh(ix),iy,iz)/absB(ixh(ix),iy,iz)**2 - &
                              pperp(ixl(ix),iy,iz)*by(ixl(ix),iy,iz)/absB(ixl(ix),iy,iz)**2)*idx(ix) -&
                             (pperp(ix,iyh(iy),iz)*bx(ix,iyh(iy),iz)/absB(ix,iyh(iy),iz)**2 - &
                              pperp(ix,iyl(iy),iz)*bx(ix,iyl(iy),iz)/absB(ix,iyl(iy),iz)**2)*idy(iy)
                    tmp = (pperpx*bx1 + pperpy*by1 + pperpz*bz1) * ib2
                    jx1(ix,iy,iz) = -(pperpx-tmp*bx1)
                    jy1(ix,iy,iz) = -(pperpy-tmp*by1)
                    jz1(ix,iy,iz) = -(pperpz-tmp*bz1)
                enddo
            enddo
        enddo
        jperpx1 = jperpx1 + jx1
        jperpy1 = jperpy1 + jy1
        jperpz1 = jperpz1 + jz1

        call calc_jdote(jx1, jy1, jz1, jmag_dote)
        call calc_averaged_currents(jx1, jy1, jz1, jmag_avg)
        if (save_jmag==1) then
            call save_current_density('jmag', jx1, jy1, jz1, ct)
        endif
        if (save_jmag_dote==1) then
            call save_field(jdote, 'jmag_dote', ct)
        endif
    end subroutine calc_perp_magnetization_current

    !---------------------------------------------------------------------------
    ! Calculate electric current due to Gradient B drift.
    ! \vect{j}_g = P_\perp\left(\frac{\vect{B}}{B^3}\right)\times\nabla B
    ! Input:
    !   ct: current time frame.
    ! Output:
    !   jgrad_avg: the averaged 3 components of electric currents.
    !   jgrad_dote the total j dot E in the box.
    !---------------------------------------------------------------------------
    subroutine calc_gradientB_drift_current(ct, jgrad_avg, jgrad_dote)
        use saving_flags, only: save_jgrad, save_jgrad_dote
        implicit none
        integer, intent(in) :: ct
        real(fp), dimension(3), intent(out) :: jgrad_avg
        real(fp), intent(out) :: jgrad_dote
        real(fp) :: bx1, by1, bz1, btot1, ib3
        real(fp) :: dbx, dby, dbz
        integer :: nx, ny, nz, ix, iy, iz

        nx = htg%nx
        ny = htg%ny
        nz = htg%nz

        do iz = 1, nz
            do iy = 1, ny
                do ix = 1, nx
                    bx1 = bx(ix, iy, iz)
                    by1 = by(ix, iy, iz)
                    bz1 = bz(ix, iy, iz)
                    btot1 = absB(ix, iy, iz)
                    ib3 = 1.0 / btot1**3
                    dbx = (absB(ixh(ix),iy,iz)-absB(ixl(ix),iy,iz))*idx(ix)
                    dby = (absB(ix,iyh(iy),iz)-absB(ix,iyl(iy),iz))*idy(iy)
                    dbz = (absB(ix,iy,izh(iz))-absB(ix,iy,izl(iz)))*idz(iz)
                    jx1(ix,iy,iz) = -(dby*bz1-dbz*by1)*pperp(ix,iy,iz) * ib3
                    jy1(ix,iy,iz) = -(dbz*bx1-dbx*bz1)*pperp(ix,iy,iz) * ib3
                    jz1(ix,iy,iz) = -(dbx*by1-dby*bx1)*pperp(ix,iy,iz) * ib3
                enddo
            enddo
        enddo
        jperpx1 = jperpx1 + jx1
        jperpy1 = jperpy1 + jy1
        jperpz1 = jperpz1 + jz1

        call calc_jdote(jx1, jy1, jz1, jgrad_dote)
        call calc_averaged_currents(jx1, jy1, jz1, jgrad_avg)
        if (save_jgrad==1) then
            call save_current_density('jgrad', jx1, jy1, jz1, ct)
        endif
        if (save_jgrad_dote==1) then
            call save_field(jdote, 'jgrad_dote', ct)
        endif
    end subroutine calc_gradientB_drift_current

    !---------------------------------------------------------------------------
    ! Calculate electric current due to diamagnetic drift.
    ! -\frac{\nabla P_\perp\times\vect{B}}{B^2}
    ! Input:
    !   ct: current time frame.
    ! Output:
    !   jdiagm_avg: the averaged 3 components of electric currents.
    !   jdiagm_dote the total j dot E in the box.
    !---------------------------------------------------------------------------
    subroutine calc_diamagnetic_drift_current(ct, jdiagm_avg, jdiagm_dote)
        use saving_flags, only: save_jdiagm, save_jdiagm_dote
        implicit none
        integer, intent(in) :: ct
        real(fp), dimension(3), intent(out) :: jdiagm_avg
        real(fp), intent(out) :: jdiagm_dote
        real(fp) :: bx1, by1, bz1, btot1, ib2
        real(fp) :: dpdx, dpdy, dpdz
        integer :: nx, ny, nz, ix, iy, iz

        nx = htg%nx
        ny = htg%ny
        nz = htg%nz

        do iz = 1, nz
            do iy = 1, ny
                do ix = 1, nx
                    bx1 = bx(ix, iy, iz)
                    by1 = by(ix, iy, iz)
                    bz1 = bz(ix, iy, iz)
                    btot1 = absB(ix, iy, iz)
                    ib2 = 1.0/(btot1*btot1)
                    dpdx = (pperp(ixh(ix),iy,iz)-pperp(ixl(ix),iy,iz))*idx(ix)
                    dpdy = (pperp(ix,iyh(iy),iz)-pperp(ix,iyl(iy),iz))*idy(iy)
                    dpdz = (pperp(ix,iy,izh(iz))-pperp(ix,iy,izl(iz)))*idz(iz)
                    jx1(ix,iy,iz) = -(dpdy*bz1-dpdz*by1)*ib2
                    jy1(ix,iy,iz) = -(dpdz*bx1-dpdx*bz1)*ib2
                    jz1(ix,iy,iz) = -(dpdx*by1-dpdy*bx1)*ib2
                enddo
            enddo
        enddo
        jperpx2 = jperpx2 + jx1
        jperpy2 = jperpy2 + jy1
        jperpz2 = jperpz2 + jz1
        jagyx = jagyx - jx1
        jagyy = jagyy - jy1
        jagyz = jagyz - jz1

        call calc_jdote(jx1, jy1, jz1, jdiagm_dote)
        call calc_averaged_currents(jx1, jy1, jz1, jdiagm_avg)
        if (save_jdiagm==1) then
            call save_current_density('jdiagm', jx1, jy1, jz1, ct)
        endif
        if (save_jdiagm_dote==1) then
            call save_field(jdote, 'jdiagm_dote', ct)
        endif
    end subroutine calc_diamagnetic_drift_current

    !---------------------------------------------------------------------------
    ! Calculate electric current due to polarization drift.
    ! -\rho_m(d\vect{u}_E/dt)\times\vect{B}/B^2, where is due to E cross B drift.
    ! \vect{u}_E and bulk flow velocity \vect{u} are very close. The latter is used
    ! in this calculation. We need the bulk velocities from the previous and
    ! latter slices to calculate dv/dt, which is the total derivative of u,
    ! so there are partial derivative term and convective term.
    ! Input:
    !   ct: current time frame.
    ! Output:
    !   jpolar_avg: the averaged 3 components of electric currents.
    !   jpolar_dote the total j dot E in the box.
    !---------------------------------------------------------------------------
    subroutine calc_polarization_drift_current(ct, jpolar_avg, jpolar_dote)
        use pre_post_hydro, only: vdx1, vdy1, vdz1, vdx2, vdy2, vdz2, nrho1, nrho2
        use saving_flags, only: save_jpolar, save_jpolar_dote
        use particle_info, only: ptl_mass
        use parameters, only: tp1, tp2
        implicit none
        integer, intent(in) :: ct
        real(fp), dimension(3), intent(out) :: jpolar_avg
        real(fp), intent(out) :: jpolar_dote
        real(fp) :: bx1, by1, bz1, btot1, ib2
        real(fp) :: dvxdt, dvydt, dvzdt, duxdt, duydt, duzdt
        real(fp) :: idt
        integer :: nx, ny, nz, ix, iy, iz

        nx = htg%nx
        ny = htg%ny
        nz = htg%nz
        if (ct > tp1 .and. ct < tp2) then
            ! Two output steps.
            idt = domain%idt * 0.5
        else
            ! The first and the last time step.
            idt = domain%idt
        endif

        if (is_rel == 1) then
            do iz = 1, nz
                do iy = 1, ny
                    do ix = 1, nx
                        bx1 = bx(ix, iy, iz)
                        by1 = by(ix, iy, iz)
                        bz1 = bz(ix, iy, iz)
                        btot1 = absB(ix, iy, iz)
                        ib2 = 1.0/(btot1*btot1)

                        ! vdx1... here is actually 4-velocity
                        ! duxdt = (vdx2(ix,iy,iz)*nrho2(ix,iy,iz) - &
                        !          vdx1(ix,iy,iz)*nrho1(ix,iy,iz)) * idt
                        ! duydt = (vdy2(ix,iy,iz)*nrho2(ix,iy,iz) - &
                        !          vdy1(ix,iy,iz)*nrho1(ix,iy,iz)) * idt
                        ! duzdt = (vdz2(ix,iy,iz)*nrho2(ix,iy,iz) - &
                        !          vdz1(ix,iy,iz)*nrho1(ix,iy,iz)) * idt

                        ! duxdt = (ux(ixh(ix),iy,iz)*num_rho(ixh(ix),iy,iz) - &
                        !          ux(ixl(ix),iy,iz)*num_rho(ixl(ix),iy,iz)) * &
                        !         vx(ix,iy,iz) * idx(ix) + &
                        !         (ux(ix,iyh(iy),iz)*num_rho(ix,iyh(iy),iz) - &
                        !          ux(ix,iyl(iy),iz)*num_rho(ix,iyl(iy),iz)) * &
                        !         vy(ix,iy,iz) * idy(iy) + &
                        !         (ux(ix,iy,izh(iz))*num_rho(ix,iy,izh(iz)) - &
                        !          ux(ix,iy,izl(iz))*num_rho(ix,iy,izl(iz))) * &
                        !         vz(ix,iy,iz) * idz(iz) + duxdt
                        ! duydt = (uy(ixh(ix),iy,iz)*num_rho(ixh(ix),iy,iz) - &
                        !          uy(ixl(ix),iy,iz)*num_rho(ixl(ix),iy,iz)) * &
                        !         vx(ix,iy,iz) * idx(ix) + &
                        !         (uy(ix,iyh(iy),iz)*num_rho(ix,iyh(iy),iz) - &
                        !          uy(ix,iyl(iy),iz)*num_rho(ix,iyl(iy),iz)) * &
                        !         vy(ix,iy,iz) * idy(iy) + &
                        !         (uy(ix,iy,izh(iz))*num_rho(ix,iy,izh(iz)) - &
                        !          uy(ix,iy,izl(iz))*num_rho(ix,iy,izl(iz))) * &
                        !         vz(ix,iy,iz) * idz(iz) + duydt
                        ! duzdt = (uz(ixh(ix),iy,iz)*num_rho(ixh(ix),iy,iz) - &
                        !          uz(ixl(ix),iy,iz)*num_rho(ixl(ix),iy,iz)) * &
                        !         vx(ix,iy,iz) * idx(ix) + &
                        !         (uz(ix,iyh(iy),iz)*num_rho(ix,iyh(iy),iz) - &
                        !          uz(ix,iyl(iy),iz)*num_rho(ix,iyl(iy),iz)) * &
                        !         vy(ix,iy,iz) * idy(iy) + &
                        !         (uz(ix,iy,izh(iz))*num_rho(ix,iy,izh(iz)) - &
                        !          uz(ix,iy,izl(iz))*num_rho(ix,iy,izl(iz))) * &
                        !         vz(ix,iy,iz) * idz(iz) + duzdt
                        duxdt = (vdx2(ix,iy,iz) - vdx1(ix,iy,iz)) * idt
                        duydt = (vdy2(ix,iy,iz) - vdy1(ix,iy,iz)) * idt
                        duzdt = (vdz2(ix,iy,iz) - vdz1(ix,iy,iz)) * idt

                        duxdt = (ux(ixh(ix),iy,iz) - ux(ixl(ix),iy,iz)) * &
                                vx(ix,iy,iz) * idx(ix) + &
                                (ux(ix,iyh(iy),iz) - ux(ix,iyl(iy),iz)) * &
                                vy(ix,iy,iz) * idy(iy) + &
                                (ux(ix,iy,izh(iz)) - ux(ix,iy,izl(iz))) * &
                                vz(ix,iy,iz) * idz(iz) + duxdt
                        duydt = (uy(ixh(ix),iy,iz) - uy(ixl(ix),iy,iz)) * &
                                vx(ix,iy,iz) * idx(ix) + &
                                (uy(ix,iyh(iy),iz) - uy(ix,iyl(iy),iz)) * &
                                vy(ix,iy,iz) * idy(iy) + &
                                (uy(ix,iy,izh(iz)) - uy(ix,iy,izl(iz))) * &
                                vz(ix,iy,iz) * idz(iz) + duydt
                        duzdt = (uz(ixh(ix),iy,iz) - uz(ixl(ix),iy,iz)) * &
                                vx(ix,iy,iz) * idx(ix) + &
                                (uz(ix,iyh(iy),iz) - uz(ix,iyl(iy),iz)) * &
                                vy(ix,iy,iz) * idy(iy) + &
                                (uz(ix,iy,izh(iz)) - uz(ix,iy,izl(iz))) * &
                                vz(ix,iy,iz) * idz(iz) + duzdt
                        jx1(ix,iy,iz) = -(duydt*bz1 - duzdt*by1) * ib2
                        jy1(ix,iy,iz) = -(duzdt*bx1 - duxdt*bz1) * ib2
                        jz1(ix,iy,iz) = -(duxdt*by1 - duydt*bx1) * ib2
                    enddo
                enddo
            enddo
            jx1 = jx1 * num_rho
            jy1 = jy1 * num_rho
            jz1 = jz1 * num_rho
        else
            do iz = 1, nz
                do iy = 1, ny
                    do ix = 1, nx
                        bx1 = bx(ix, iy, iz)
                        by1 = by(ix, iy, iz)
                        bz1 = bz(ix, iy, iz)
                        btot1 = absB(ix, iy, iz)
                        ib2 = 1.0/(btot1*btot1)

                        dvxdt = (vdx2(ix,iy,iz)*nrho2(ix,iy,iz) - &
                                 vdx1(ix,iy,iz)*nrho1(ix,iy,iz)) * idt
                        dvydt = (vdy2(ix,iy,iz)*nrho2(ix,iy,iz) - &
                                 vdy1(ix,iy,iz)*nrho1(ix,iy,iz)) * idt
                        dvzdt = (vdz2(ix,iy,iz)*nrho2(ix,iy,iz) - &
                                 vdz1(ix,iy,iz)*nrho1(ix,iy,iz)) * idt

                        dvxdt = (vx(ixh(ix),iy,iz)*num_rho(ixh(ix),iy,iz) - &
                                 vx(ixl(ix),iy,iz)*num_rho(ixl(ix),iy,iz)) * &
                                vx(ix,iy,iz) * idx(ix) + &
                                (vx(ix,iyh(iy),iz)*num_rho(ix,iyh(iy),iz) - &
                                 vx(ix,iyl(iy),iz)*num_rho(ix,iyl(iy),iz)) * &
                                vy(ix,iy,iz) * idy(iy) + &
                                (vx(ix,iy,izh(iz))*num_rho(ix,iy,izh(iz)) - &
                                 vx(ix,iy,izl(iz))*num_rho(ix,iy,izl(iz))) * &
                                vz(ix,iy,iz) * idz(iz) + dvxdt
                        dvydt = (vy(ixh(ix),iy,iz)*num_rho(ixh(ix),iy,iz) - &
                                 vy(ixl(ix),iy,iz)*num_rho(ixl(ix),iy,iz)) * &
                                vx(ix,iy,iz) * idx(ix) + &
                                (vy(ix,iyh(iy),iz)*num_rho(ix,iyh(iy),iz) - &
                                 vy(ix,iyl(iy),iz)*num_rho(ix,iyl(iy),iz)) * &
                                vy(ix,iy,iz) * idy(iy) + &
                                (vy(ix,iy,izh(iz))*num_rho(ix,iy,izh(iz)) - &
                                 vy(ix,iy,izl(iz))*num_rho(ix,iy,izl(iz))) * &
                                vz(ix,iy,iz) * idz(iz) + dvydt
                        dvzdt = (vz(ixh(ix),iy,iz)*num_rho(ixh(ix),iy,iz) - &
                                 vz(ixl(ix),iy,iz)*num_rho(ixl(ix),iy,iz)) * &
                                vx(ix,iy,iz) * idx(ix) + &
                                (vz(ix,iyh(iy),iz)*num_rho(ix,iyh(iy),iz) - &
                                 vz(ix,iyl(iy),iz)*num_rho(ix,iyl(iy),iz)) * &
                                vy(ix,iy,iz) * idy(iy) + &
                                (vz(ix,iy,izh(iz))*num_rho(ix,iy,izh(iz)) - &
                                 vz(ix,iy,izl(iz))*num_rho(ix,iy,izl(iz))) * &
                                vz(ix,iy,iz) * idz(iz) + dvzdt
                        jx1(ix,iy,iz) = -(dvydt*bz1 - dvzdt*by1) * ib2
                        jy1(ix,iy,iz) = -(dvzdt*bx1 - dvxdt*bz1) * ib2
                        jz1(ix,iy,iz) = -(dvxdt*by1 - dvydt*bx1) * ib2
                    enddo
                enddo
            enddo
        endif

        jx1 = jx1 * ptl_mass
        jy1 = jy1 * ptl_mass
        jz1 = jz1 * ptl_mass

        jperpx1 = jperpx1 + jx1
        jperpy1 = jperpy1 + jy1
        jperpz1 = jperpz1 + jz1
        jperpx2 = jperpx2 + jx1
        jperpy2 = jperpy2 + jy1
        jperpz2 = jperpz2 + jz1

        call calc_jdote(jx1, jy1, jz1, jpolar_dote)
        call calc_averaged_currents(jx1, jy1, jz1, jpolar_avg)
        if (save_jpolar==1) then
            call save_current_density('jpolar', jx1, jy1, jz1, ct)
        endif
        if (save_jpolar_dote==1) then
            call save_field(jdote, 'jpolar_dote', ct)
        endif
    end subroutine calc_polarization_drift_current

    !---------------------------------------------------------------------------
    ! Electric current due to E cross B drift.
    ! \rho E cross B / B^2
    ! Input:
    !   ct: current time frame.
    ! Output:
    !   jexb_avg: the averaged 3 components of electric currents.
    !   jexb_dote the total j dot E in the box.
    !---------------------------------------------------------------------------
    subroutine calc_exb_drift_current(ct, jexb_avg, jexb_dote)
        use particle_info, only: ptl_charge
        use saving_flags, only: save_jexb, save_jexb_dote
        implicit none
        integer, intent(in) :: ct
        real(fp), dimension(3), intent(out) :: jexb_avg
        real(fp), intent(out) :: jexb_dote
        real(fp) :: bx1, by1, bz1, btot1, ib2, nrho
        integer :: nx, ny, nz, ix, iy, iz

        nx = htg%nx
        ny = htg%ny
        nz = htg%nz

        do iz = 1, nz
            do iy = 1, ny
                do ix = 1, nx
                    bx1 = bx(ix, iy, iz)
                    by1 = by(ix, iy, iz)
                    bz1 = bz(ix, iy, iz)
                    btot1 = absB(ix, iy, iz)
                    ib2 = 1.0/(btot1*btot1)
                    nrho = num_rho(ix,iy,iz)
                    jx1(ix,iy,iz) = nrho * ptl_charge * &
                        (ey(ix,iy,iz)*bz1-ez(ix,iy,iz)*by1)*ib2
                    jy1(ix,iy,iz) = nrho * ptl_charge * &
                        (ez(ix,iy,iz)*bx1-ex(ix,iy,iz)*bz1)*ib2
                    jz1(ix,iy,iz) = nrho * ptl_charge * &
                        (ex(ix,iy,iz)*by1-ey(ix,iy,iz)*bx1)*ib2
                enddo
            enddo
        enddo
        jperpx1 = jperpx1 + jx1
        jperpy1 = jperpy1 + jy1
        jperpz1 = jperpz1 + jz1
        jperpx2 = jperpx2 + jx1
        jperpy2 = jperpy2 + jy1
        jperpz2 = jperpz2 + jz1

        call calc_jdote(jx1, jy1, jz1, jexb_dote)
        call calc_averaged_currents(jx1, jy1, jz1, jexb_avg)
        if (save_jexb==1) then
            call save_current_density('jexb', jx1, jy1, jz1, ct)
        endif
        if (save_jexb_dote==1) then
            call save_field(jdote, 'jexb_dote', ct)
        endif
    end subroutine calc_exb_drift_current

    !---------------------------------------------------------------------------
    ! Electric current parallel and perpendicular to magnetic field B for
    ! single fluid. The current is directly from PIC simulation results.
    ! The parallel component is $\vect{j}_\parallel = (\vect{j}\cdot\vect{B})
    ! \vect{B}/B^2$. The perpendicular component is $\vect{j}-\vect{j}_\parallel$
    ! Input:
    !   ct: current time frame.
    ! Output:
    !   jpara_avg, jperp_avg: the averaged 3 components of electric currents.
    !   jpara_dote, jperp_dote: the total j dot E in the box.
    !---------------------------------------------------------------------------
    subroutine calc_current_single_fluid(ct, jpara_avg, jperp_avg, &
                                         jpara_dote, jperp_dote)
        use saving_flags, only: save_jpara, save_jperp, save_jpara_dote, &
                save_jperp_dote
        implicit none
        integer, intent(in) :: ct
        real(fp), intent(out) :: jpara_dote, jperp_dote
        real(fp), dimension(3), intent(out) :: jpara_avg, jperp_avg
        real(fp), allocatable, dimension(:, :, :) :: jdotb_over_b2
        allocate(jdotb_over_b2(htg%nx, htg%ny, htg%nz))
        jdotb_over_b2 = (jx*bx+jy*by+jz*bz)/(absB*absB)
        ! Parallel direction
        jx1 = jdotb_over_b2 * bx
        jy1 = jdotb_over_b2 * by
        jz1 = jdotb_over_b2 * bz
        ! Perpendicular direction
        jx2 = jx - jx1
        jy2 = jy - jy1
        jz2 = jz - jz1

        deallocate(jdotb_over_b2)
        call calc_jdote(jx1, jy1, jz1, jpara_dote)
        if (save_jpara==1) then
            call save_current_density('jpara', jx1, jy1, jz1, ct)
        endif
        if (save_jpara_dote==1) then
            call save_field(jdote, 'jpara_dote', ct)
        endif
        call calc_jdote(jx2, jy2, jz2, jperp_dote)
        if (save_jperp==1) then
            call save_current_density('jperp', jx2, jy2, jz2, ct)
        endif
        if (save_jperp_dote==1) then
            call save_field(jdote, 'jperp_dote', ct)
        endif
        call calc_averaged_currents(jx1, jy1, jz1, jpara_avg)
        call calc_averaged_currents(jx2, jy2, jz2, jperp_avg)
    end subroutine calc_current_single_fluid

    !---------------------------------------------------------------------------
    ! Electric current calculated directly from q*n*u, where q is the particle
    ! charge, n is the particle number density, u is the bulk velocities of the
    ! particles. 
    ! Input:
    !   ct: current time frame.
    ! Output:
    !   jqnvpara_avg, jqnvperp_avg: the averaged 3 components of electric currents.
    !   jqnvpara_dote, jqnvperp_dote: the total j dot E in the box.
    !---------------------------------------------------------------------------
    subroutine calc_qnv_current(ct, jqnvpara_avg, jqnvperp_avg, &
                                jqnvpara_dote, jqnvperp_dote)
        use particle_info, only: ptl_charge
        use saving_flags, only: save_jqnvpara, save_jqnvperp, &
                save_jqnvpara_dote, save_jqnvperp_dote
        implicit none
        integer, intent(in) :: ct
        real(fp), intent(out) :: jqnvpara_dote, jqnvperp_dote
        real(fp), dimension(3), intent(out) :: jqnvpara_avg, jqnvperp_avg
        real(fp), allocatable, dimension(:, :, :) :: qnvx, qnvy, qnvz, qnv_dotb
        allocate(qnvx(htg%nx, htg%ny, htg%nz))
        allocate(qnvy(htg%nx, htg%ny, htg%nz))
        allocate(qnvz(htg%nx, htg%ny, htg%nz))
        allocate(qnv_dotb(htg%nx, htg%ny, htg%nz))
        qnvx = ptl_charge*num_rho*vx
        qnvy = ptl_charge*num_rho*vy
        qnvz = ptl_charge*num_rho*vz
        qnv_dotb = (qnvx*bx+qnvy*by+qnvz*bz) / (absB*absB)
        ! Parallel direction
        jx1 = qnv_dotb * bx
        jy1 = qnv_dotb * by
        jz1 = qnv_dotb * bz
        ! Perpendicular direction
        jx2 = qnvx - jx1
        jy2 = qnvy - jy1
        jz2 = qnvz - jz1

        deallocate(qnvx, qnvy, qnvz, qnv_dotb)
        call calc_jdote(jx1, jy1, jz1, jqnvpara_dote)
        if (save_jqnvpara==1) then
            call save_current_density('jqnvpara', jx1, jy1, jz1, ct)
        endif
        if (save_jqnvpara_dote==1) then
            call save_field(jdote, 'jqnvpara_dote', ct)
        endif
        call calc_jdote(jx2, jy2, jz2, jqnvperp_dote)
        if (save_jqnvperp==1) then
            call save_current_density('jqnvperp', jx2, jy2, jz2, ct)
        endif
        if (save_jqnvperp_dote==1) then
            call save_field(jdote, 'jqnvperp_dote', ct)
        endif
        call calc_averaged_currents(jx1, jy1, jz1, jqnvpara_avg)
        call calc_averaged_currents(jx2, jy2, jz2, jqnvperp_avg)
    end subroutine calc_qnv_current


    !---------------------------------------------------------------------------
    ! Calculate current density due to the compressibility.
    ! [-(\nabla\cdot\vect{u})\vect{u}\times\vect{B}/B^2]\cdot\vect{E}
    ! Input:
    !   ct: current time frame.
    ! Output:
    !   jdivv_avg: the averaged 3 components of electric currents.
    !   jdivv_dote: the total j dot E in the box.
    !---------------------------------------------------------------------------
    subroutine calc_compression_current(ct, jdivv_avg, jdivv_dote)
        use particle_info, only: ptl_mass
        use compression_shear, only: div_v, calc_div_v
        use saving_flags, only: save_jdivv, save_jdivv_dote
        implicit none
        integer, intent(in) :: ct
        real(fp), dimension(3), intent(out) :: jdivv_avg
        real(fp), intent(out) :: jdivv_dote
        call calc_div_v
        if (is_rel == 1) then
            jx1 = div_v * (uz*by - uy*bz) / (absB*absB)
            jy1 = div_v * (ux*bz - uz*bx) / (absB*absB)
            jz1 = div_v * (uy*bx - ux*by) / (absB*absB)
        else
            jx1 = div_v * (vz*by - vy*bz) / (absB*absB)
            jy1 = div_v * (vx*bz - vz*bx) / (absB*absB)
            jz1 = div_v * (vy*bx - vx*by) / (absB*absB)
        endif
        jx1 = jx1 * num_rho * ptl_mass
        jy1 = jy1 * num_rho * ptl_mass
        jz1 = jz1 * num_rho * ptl_mass

        call calc_jdote(jx1, jy1, jz1, jdivv_dote)
        call calc_averaged_currents(jx1, jy1, jz1, jdivv_avg)
        if (save_jdivv==1) then
            call save_current_density('jdivv', jx1, jy1, jz1, ct)
        endif
        if (save_jdivv_dote==1) then
            call save_field(jdote, 'jdivv_dote', ct)
        endif
    end subroutine calc_compression_current

    !---------------------------------------------------------------------------
    ! Save calculated electric currents.
    ! Input:
    !   cvar: the name of the electric current.
    !   jx, jy, jz: 3 components of the data set.
    !   ct: current time frame.
    !---------------------------------------------------------------------------
    subroutine save_current_density(qname, jx, jy, jz, ct)
        use mpi_module
        use constants, only: fp
        use mpi_datatype_fields, only: subsizes_ghost
        use mpi_io_fields, only: save_field
        implicit none
        character(*), intent(in) :: qname
        integer, intent(in) :: ct
        real(fp), dimension(:, :, :), intent(in) :: jx, jy, jz
        character(len=15) :: qname1

        qname1 = qname//'x' 
        call save_field(jx, trim(adjustl(qname1)), ct)
        qname1 = qname//'y' 
        call save_field(jy, trim(adjustl(qname1)), ct)
        qname1 = qname//'z' 
        call save_field(jz, trim(adjustl(qname1)), ct)
    end subroutine save_current_density


    !---------------------------------------------------------------------------
    ! Get averaged electric currents.
    ! Input:
    !   jx, jy, jz: the 3 components of electric current.
    ! Output:
    !   javg: the averaged 3 components of electric currents.
    !---------------------------------------------------------------------------
    subroutine calc_averaged_currents(jx, jy, jz, javg)
        use mpi_module
        use constants, only: fp
        use mpi_datatype_fields, only: subsizes_ghost
        use statistics, only: get_average_and_total
        implicit none
        real(fp), dimension(:, :, :), intent(in) :: jx, jy, jz
        real(fp), dimension(3), intent(out) :: javg
        real(fp) :: tot
        call get_average_and_total(jx, javg(1), tot)
        call get_average_and_total(jy, javg(2), tot)
        call get_average_and_total(jz, javg(3), tot)
    end subroutine calc_averaged_currents

    !---------------------------------------------------------------------------
    ! Save the current density averaged over the simulation box.
    !---------------------------------------------------------------------------
    subroutine save_averaged_current
        use constants, only: fp
        use parameters, only: tp1, tp2
        use particle_info, only: species, ibtag
        implicit none
        integer :: pos1, output_record
        integer :: ct
        logical :: dir_e

        inquire(file='./data/.', exist=dir_e)
        if (.not. dir_e) then
            call system('mkdir ./data')
        endif
        print*, "Saving current densities..."

        open(unit=61,&
            file='data/current'//ibtag//'_'//species//'.gda',access='stream',&
            status='unknown',form='unformatted',action='write')
        do ct = tp1, tp2
            output_record = ct - tp1 + 1
            pos1 = (output_record-1)*sizeof(fp)*3*ncurrents + 1
            write(61, pos=pos1) javg(:,:,output_record)
        enddo
        close(61)
    end subroutine save_averaged_current

end module current_densities
