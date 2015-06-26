!*******************************************************************************
! Module for reading configuration file. The configuration file looks like
! A = value or A: value. So this module defines a subroutine to read the value
! with different delimiter.
!*******************************************************************************
module read_config
    implicit none
    private
    public get_variable, get_variable_int

    contains

    !---------------------------------------------------------------------------
    ! Function to the value of one variable with name var_name.
    ! Inputs:
    !   fh: file handler.
    !   var_name: the variable name.
    !   delimiter: the delimiter. The value of the variable is after the delimiter.
    ! Returns:
    !   var_value: the variable value.
    !---------------------------------------------------------------------------
    function get_variable(fh, var_name, delimiter) result(var_value)
        use constants, only: fp
        implicit none
        integer, intent(in) :: fh
        character(*), intent(in) :: var_name, delimiter
        real(fp) :: var_value
        character(len=150) :: single_line
        do while (index(single_line, var_name) == 0)
            read(fh, '(A)') single_line
        enddo
        read(single_line(index(single_line, delimiter)+1:), *) var_value
    end function

    !---------------------------------------------------------------------------
    ! Get the variable as an integer.
    !---------------------------------------------------------------------------
    function get_variable_int(fh, var_name, delimiter) result(var_value_int)
        implicit none
        use constants, only: fp
        implicit none
        integer, intent(in) :: fh
        character(*), intent(in) :: var_name, delimiter
        real(fp) :: var_value
        integer :: var_value_int

        var_value = get_variable(fh, var_name, delimiter)
        var_value_int = int(var_value)
    end function get_variable_int

module read_config
